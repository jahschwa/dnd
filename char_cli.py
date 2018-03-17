#!/usr/bin/env python3

# ===== WORKING EXAMPLES =====
#
# >>> new
# >>> set stat dexterity 17
# >>> get stat ac
# r-  13 ac (b:0/0 ?:0/0)
#
# >>> g s ac
# r-  13 ac (b:0/0 ?:0/0)
#
# >>> add bonus mage_armor 4 ac armor
# >>> get stat ac,ac_ff,ac_touch
# r-  17 ac (b:1/1 ?:0/0)
# r-  14 ac_ff (b:1/1 ?:0/0)
# r-  13 ac_touch (b:0/0 ?:0/0)
#
# >>> off mage_armor
# >>> get stat ac,ff,touch
# r-  13 ac (b:1/1 ?:0/0)
# r-  10 ac_ff (b:1/1 ?:0/0)
# r-  13 ac_touch (b:0/0 ?:0/0)
#
# >>> all bonus mage_armor
#   value | 4
#  active | False
#    type | armor
#  revert | same
#   stats | _ac_armor
# conditn |
#    text |
#
# ===== PLANNED FOR THE FUTURE =====
#
# >>> get ac,ac_ff,ac_touch with mage_armor
# r-  17 ac (b:1/1 ?:0/0)
# r-  14 ac_ff (b:1/1 ?:0/0)
# r-  13 ac_touch (b:0/0 ?:0/0)
#
# >>> get stat ac,ff,touch
# r-  13 ac (b:1/1 ?:0/0)
# r-  10 ac_ff (b:1/1 ?:0/0)
# r-  13 ac_touch (b:0/0 ?:0/0)

# ===== QUICK COMMAND LISTING =====
#
# implemented types: stat bonus text
#
# load
# new
# save
#
# search [name]
# get [type] [name]
# set [type] name [options]
# add type name [options]
# del type name
# all type name
# on bonus
# off bonus
# revert bonus
#
# eval command
# exec command
# trace
#
# ===== NOT IMPLEMENTED =====
# time num [rd|min|hr|day]
# ++
# use name
# reset [name]
# revert

# ===== TODO =====
#
# [TODO] help text
# [TODO] autocompletions
# [TODO] consider managing multiple characters
# [TODO] better exception messages, especially for num args
# [TODO] dice roller
# [TODO] custom aliases?
# [TODO] actual modificaion tracking for save prompting

import sys,os,pickle,cmd,inspect,traceback

import char

# keep running forever unless we get EOF from the CLI (i.e. a clean return)
# if we get a KeyboardInterrupt resume the loop
# @param fname (None,str) [None] the file to open
def main(fname=None):

  cli = CLI(fname)
  run = True
  print('')
  while run:
    try:
      cli.cmdloop()
      run = False
    except KeyboardInterrupt:
      print('use Ctrl+D / EOF to exit')
      pass

# thrown when the user passes non-matching arguments to a command
# @param sig (str) the signature of the target command
# @param msg (str) error message
class ArgsError(Exception):
  def __init__(self,sig,msg):
    super(ArgsError,self).__init__(msg)
    self.sig = sig

# the Cmd class expects a static string but let's bootstrap it to be dynamic
class Prompt(object):

  # @param func (func) the function to generate the prompt
  def __init__(self,func):
    self.func = func

  # the Cmd class just calls a print, so we can trick it with this override
  # @return (str)
  def __str__(self):
    return str(self.func())

###############################################################################
# CLI class
#   - does alot of customization to the base cmd.Cmd
#   - dynamically loads commands from a Character
#   - advanced argument parsing
#     - quote blocking
#     - creates lists from any arg with commas that wasn't quoted
#     - keyword args e.g. "text=foo"
###############################################################################

class CLI(cmd.Cmd):

############################ <DEV>

  def do_eval(self,args):
    """[DEV] run eval() on input"""

    try:
      print(eval(' '.join(args)))
    except:
      print(traceback.format_exc())

  def do_exec(self,args):
    """[DEV] run exec() on input"""

    try:
      exec(' '.join(args))
    except:
      print(traceback.format_exc())

  def do_trace(self,args):
    """[DEV] print traceback for last exception"""

    print(self.last_trace)

  def do_args(self,args):
    """[DEV] print args"""

    print(args)

  def do_old_load(self,args):

    if not args:
      print('Missing file name')
      return
    if not self.overwrite():
      return
    if not os.path.isfile(args[0]):
      print('Unable to read "%s"' % args[0])
      return
    try:
      with open(args[0],'rb') as f:
        self.plug(pickle.load(f))
        self.fname = args[0]
        self.modified = False
    except Exception:
      print('Unable to unpickle "%s"' % args[0])

  def do_old_save(self,args):

    fname = self.fname if not args else ' '.join(args)
    if not fname:
      fname = input('Enter a file name: ')
    try:
      with open(fname,'a') as f:
        pass
    except:
      print('Unable to write "%s"' % fname)
      return
    try:
      with open(fname,'wb') as f:
        pickle.dump(self.char,f,-1)
      self.fname = fname
      self.modified = False
      return False
    except:
      print('Unable to pickle character')

############################ </DEV>

  # @param fname (None,str) file name to load if not None
  def __init__(self,fname):

    cmd.Cmd.__init__(self)
    self.prompt = Prompt(self.get_prompt)

    self.fname = fname
    self.char = None
    self.exported = {}
    self.modified = False
    self.last_trace = 'No logged traceback'
    if fname:
      self.do_load([fname])

  # we expect this to get overriden by our Character
  # @return (str)
  def get_prompt(self):

    if not self.char:
      return '[ --- none --- ] '

    prompt = self.char._get_prompt()

    # the readline library doesn't seem to like prompts containing newlines
    # so print them manually and only return the final line to our parent
    if '\n' in prompt:
      prompt = prompt.split('\n')
      while len(prompt)>1:
        print(prompt.pop(0))
      prompt = prompt[0]
    return prompt

  # @param line (str)
  # @return (3-tuple)
  #   #0 (str) command name
  #   #1 (list) args to pass to the command
  #   #2 (str) the original string
  def parseline(self,line):

    (args,kwargs) = self.get_args(line)
    return (args[0] if args else '',args[1:],line)

  # @param line (str) a command string
  # @param lower (bool) [False] whether to lowercase everything
  # @param split (bool) [True] turn args containing commas into list objects
  # @return (2-tuple)
  #   #0 (list of (str OR list)) space-separated args
  #   #1 (dict of name:(str OR list)) keyword arguments
  def get_args(self,line,lower=False,split=True):
    """get space-separated args accounting for quotes"""

    args = []
    kwargs = {}
    quote = False
    last_quoted = False
    to_lower = lower
    s = ''
    for (i,c) in enumerate(line.strip()+' '):

      # separate on spaces unless inside quotes
      if c==' ':
        if quote:
          s += c
        elif s:
          if not last_quoted and split and ',' in s:
            x = s.split(',')

            # differentiate args and kwargs
            if '=' in x[0]:
              (key,x[0]) = x[0].split('=')
              kwargs[key] = x
            else:
              args.append(x)
          else:

            #differentiate args and kwargs
            if '=' in s:
              (key,x) = s.split('=')
              kwargs[key] = x
            else:
              args.append(s)
          last_quoted = False
          s = ''

      # keep track of quotes
      elif c=='"':
        if quote:
          quote = False
          to_lower = lower
        else:
          quote = True
          last_quoted = True
          to_lower = False

      # add characters to the current string
      else:
        if to_lower:
          s += c.lower()
        else:
          s += c

    return (args,kwargs)

  # just print the prompt again if the user enters nothing
  def emptyline(self):
    pass

  # add an extra newline after command output so the interface looks better
  # @param stop (bool)
  # @param line (str)
  def postcmd(self,stop,line):

    print('')
    return stop

  def do_EOF(self,args):
    """exit the CLI (prompts for save)"""

    if self.overwrite():
      return True

  def do_help(self,args):
    """show help text for commands"""

    # find the referenced comand or sub-command
    if args and args[0] in self.exported:
      func = self.exported[args[0]]
      if isinstance(func,dict):
        if len(args)<2 or args[1] not in func:
          print('*** Unknown or missing sub-command')
          return
        func = func[args[1]]

      # first line is always the signature
      print('')
      print('# '+self.get_sig(func)[0])

      # look for __doc__ text in the function ot its parent
      if not func.__doc__:
        func = getattr(super(self.char.__class__,self.char),func.__name__)

      # be smart about formatting leading indents and newlines
      if func.__doc__:
        lines = [x.rstrip() for x in func.__doc__.split('\n')]
        while len(lines) and not lines[0].strip():
          del lines[0]
        while len(lines) and not lines[-1].strip():
          del lines[-1]
        leading = len(lines[0])-len(lines[0].lstrip())
        if leading>0:
          lines = [x[leading:] for x in lines]
        print('#')
        print('\n'.join(['# '+x for x in lines]))

    # if the requested function is defined here rather than in our Character
    # just use the cmd.Cmd built-in help method
    else:
      cmd.Cmd.do_help(self,' '.join(args))

  def do_load(self,args):
    """load a character from a file"""

    if not args:
      print('Missing file name')
    elif not self.overwrite():
      return
    elif not os.path.isfile(args[0]):
      print('Unable to read "%s"' % args[0])
    else:
      (c,errors) = char.Character.load(args[0])

      # print semi-detailed errors to help with debugging
      if errors:
        print('Failed to load "%s"' % args[0])
        print('\n'.join(errors))
      else:
        self.unplug()
        self.plug(c)
        self.fname = args[0]
        self.modified = False

  # @return (bool) if saving was successful
  def do_save(self,args):
    """save a character to a file"""

    fname = self.fname if not args else ' '.join(args)
    if not fname:
      fname = input('Enter a file name: ')
    try:
      with open(fname,'a') as f:
        pass
    except:
      print('Unable to write to "%s"' % fname)
      return False

    self.char.save(fname)
    self.fname = fname
    self.modified = False

    return True

  def do_close(self,args):
    """close the current character (prompts for save)"""

    if not self.char:
      return
    if self.overwrite():
      self.unplug()

  # check if the character has been modified and prompt for save
  # @return (bool) if it's okay to trash our current character data
  def overwrite(self):

    if self.char is None or not self.modified:
      return True
    choice = input('\nSave changes to current char? (Y/n/c): ').lower()
    if choice in ('','y','yes'):
      return self.do_save([])==False
    if choice in ('n','no'):
      return True
    return False

  # if the commnd doesn't match any defined in this file, use those exported
  # by our Character instead; also checks for argument matching
  # @param line (str) raw command text
  def default(self,line):

    (args,kwargs) = self.get_args(line)

    # pull command or sub-command function from exported
    if args[0] in self.exported:
      val = self.exported[args[0]]
      if isinstance(val,dict):
        if len(args)<2:
          print('Missing sub-command')
          return
        elif args[1] in val:
          (func,args) = (val[args[1]],args[2:])
        else:
          print('Unknown sub-command "%s"' % args[1])
          return
      else:
        (func,args) = (val,args[1:])
    else:
      print('Unknown command "%s"' % args[0])
      return

    # check for matching args/kwargs and print error+signature if failed
    try:
      self.check_args(func,args,kwargs)
      result = func(*args,**kwargs)
    except ArgsError as e:
      print('*** ArgsError: %s' % e.args[0])
      print('    %s' % e.sig)
      return

    # print generic exceptions and log them in last_trace for later
    except:
      s = traceback.format_exc()
      self.last_trace = s.strip()
      print('*** '+s.split('\n')[-2])
      return

    # print anything returned by the function
    if result:
      print(result)

  # compare user-provided args/kwargs to the command signature
  # @param func (func) the function to use as reference
  # @param user_args (list)
  # @param user_kwargs (dict)
  # @raise ArgsError
  def check_args(self,func,user_args,user_kwargs):

    (sig,args,kwargs) = self.get_sig(func)
    if len(user_args)<len(args):
      raise ArgsError(sig,'missing required args')

    if len(user_args)>len(args+kwargs):
      raise ArgsError(sig,'too many args')

    for key in user_kwargs:
      if key not in kwargs:
        raise ArgsError(sig,'unknown keyword "%s"' % key)

  # inspect a function and parse out its signature
  # @param func (func)
  # @return (3-tuple)
  #   #0 (str) user-readable signature
  #   #1 (list) argument names
  #   #2 (list) keyword argument names
  def get_sig(self,func):

    (args,varargs,keywords,defaults) = inspect.getargspec(func)
    args.remove('self')
    split = -len(defaults) if defaults else 0
    kwargs = args[split:] if split else []
    args = args[:split] if split else args

    # account for sub commands e.g. "set_stat"
    name = func.__name__.replace('_',' ')

    opts = ['[%s]' % s for s in kwargs]
    space = ' ' if args and opts else ''
    sig = '(%s) %s%s%s' % (name,' '.join(args),space,' '.join(opts))

    return (sig,args,kwargs)

  # pull in exported commands and aliases from the Character
  # @param char (Character)
  def plug(self,char):

    self.unplug()
    self.char = char

    # basic commands
    self.exported = {name:getattr(char,name) for name in char.export}

    # sub commands e.g. "set_stat"
    funcs = inspect.getmembers(char,inspect.ismethod)
    for prefix in char.export_prefix:
      self.exported[prefix] = {}
      for (name,func) in funcs:
        if name.startswith(prefix+'_'):
          name = name[len(prefix)+1:]
          self.exported[prefix][name] = func

    # basic aliases
    for (alias,target) in char.export_alias.items():
      self.exported[alias] = self.exported[target]

    # sub-command aliases
    for (alias,target) in char.export_sub_alias.items():
      for prefix in char.export_prefix:
        self.exported[prefix][alias] = self.exported[prefix][target]

  def unplug(self):

    self.char = None
    self.exported = {}

  # defaults to a Pathfinder character
  def do_new(self,args):
    """create a new character"""

    if not self.overwrite():
      return
    args = args[0] if args else 'Pathfinder'
    self.plug(eval('char.%s()' % args))
    self.modified = True

if __name__=='__main__':

  args = sys.argv
  fname = None
  if len(args)>1:
    if os.path.isfile(args[1]):
      fname = args[1]
    else:
      print('Unable to open "%s"' % args[1])
  main(fname)
