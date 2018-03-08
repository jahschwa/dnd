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

import sys,os,pickle,cmd,inspect,traceback

import char

def main(fname):

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

class ArgsError(Exception):
  pass

class Prompt(object):

  def __init__(self,func):
    self.func = func

  def __str__(self):
    return str(self.func())

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

  def get_prompt(self):

    if not self.char:
      return '[ --- none --- ] '

    prompt = self.char._get_prompt()
    if '\n' in prompt:
      prompt = prompt.split('\n')
      while len(prompt)>1:
        print(prompt.pop(0))
      prompt = prompt[0]
    return prompt

  def parseline(self,line):

    args = self.get_args(line)
    return (args[0] if args else '',args[1:],line)

  # @param args (str) a command string
  # @param lower (bool) [False] whether to lowercase everything
  # @return (list) space-separated args, without quotes commas create a list
  def get_args(self,args,lower=False,split=True):
    """get space-separated args accounting for quotes"""

    l = []
    quote = False
    last_quoted = False
    to_lower = lower
    s = ''
    for (i,c) in enumerate(args+' '):

      # separate on spaces unless inside quotes
      if c==' ' or i==len(args):
        if quote:
          s += c
        elif s:
          if not last_quoted and split:
            l.append(s.split(',') if ',' in s else s)
          else:
            l.append(s)
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

    return l

  def emptyline(self):
    pass

  def postcmd(self,stop,line):

    print('')
    return stop

  def do_EOF(self,line):
    """exit the CLI (prompts for save)"""

    if self.overwrite():
      return True

  def do_help(self,args):
    """show help text for commands"""

    if args and args[0] in self.exported:
      func = self.exported[args[0]]
      if isinstance(func,dict):
        if len(args)<2 or args[1] not in func:
          print('*** Unknown or missing sub-command')
          return
        func = func[args[1]]
      print('')
      print('# '+self.get_sig(func)[0])
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
      if errors:
        print('Failed to load "%s"' % args[0])
        print('\n'.join(errors))
      else:
        self.unplug()
        self.plug(c)
        self.fname = args[0]
        self.modified = False

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
      return

    self.char.save(fname)
    self.fname = fname
    self.modified = False

  def do_close(self,args):
    """close the current character (prompts for save)"""

    if not self.char:
      return
    if self.overwrite():
      self.unplug()

  def overwrite(self):

    if self.char is None or not self.modified:
      return True
    choice = input('\nSave changes to current char? (Y/n/c): ').lower()
    if choice in ('','y','yes'):
      return self.do_save([])==False
    if choice in ('n','no'):
      return True
    return False

  def default(self,line):

    args = self.get_args(line)
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

    try:
      self.check_args(func,args)
      result = func(*args)
    except:
      s = traceback.format_exc()
      self.last_trace = s.strip()
      print('*** '+s.split('\n')[-2])
      return
    if result:
      print(result)

  def check_args(self,func,user_args):

    (sig,args,kwargs) = self.get_sig(func)
    if len(user_args)<len(args) or len(user_args)>len(args+kwargs):
      raise ArgsError(sig)

  def get_sig(self,func):

    (args,varargs,keywords,defaults) = inspect.getargspec(func)
    args.remove('self')
    split = -len(defaults) if defaults else 0
    kwargs = args[split:] if split else []
    args = args[:split] if split else args

    name = func.__name__.replace('_',' ')
    opts = ['[%s]' % s for s in kwargs]
    space = ' ' if args and opts else ''
    sig = '(%s) %s%s%s' % (name,' '.join(args),space,' '.join(opts))

    return (sig,args,kwargs)

  def plug(self,char):

    self.unplug()
    self.char = char

    self.exported = {name:getattr(char,name) for name in char.export}

    funcs = inspect.getmembers(char,inspect.ismethod)
    for prefix in char.export_prefix:
      self.exported[prefix] = {}
      for (name,func) in funcs:
        if name.startswith(prefix+'_'):
          name = name[len(prefix)+1:]
          self.exported[prefix][name] = func

    for (alias,target) in char.export_alias.items():
      self.exported[alias] = self.exported[target]

    for (alias,target) in char.export_sub_alias.items():
      for prefix in char.export_prefix:
        self.exported[prefix][alias] = self.exported[prefix][target]

  def unplug(self):

    self.char = None
    self.exported = {}

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
