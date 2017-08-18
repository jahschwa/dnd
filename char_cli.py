#!/usr/bin/env python

#def stat ac_dex 3
#def stat ac_armor 0
#def stat ff 10+ac_armor
#def stat touch 10+ac_dex
#def stat ac 10+ac_dex+ac_armor
#get ac
#> 13
#def bonus mage_armor ac_armor +4
#get ac,ff,touch
#> 13,10,13
#get ac,ff,touch with mage_armor
#> 17,14,13
#active mage_armor
#get ac,ff,touch
#> 17,14,13

# get [type] [name]
# set [type] name [options]
# new type name [options]
# on/off name
# time num [rd|min|hr|day]
# ++
# use name
# reset [name]
# revert [name]

# [TODO] help text
# [TODO] autocompletions
# [TODO] consider managing multiple characters

import sys,os,pickle,cmd,inspect

import char

############################ <DEV>
import traceback
############################ </DEV>

def main(fname):

  cli = CLI(fname)
  run = True
  print ''
  while run:
    try:
      cli.cmdloop()
      run = False
    except KeyboardInterrupt:
      print 'use Ctrl+D / EOF to exit'
      pass

class Prompt(object):

  def __init__(self,func):
    self.func = func

  def __str__(self):
    return str(self.func())

class CLI(cmd.Cmd):

############################ <DEV>

  def do_echo(self,args):
    print args

  def do_eval(self,args):
    try:
      print eval(' '.join(args))
    except Exception as e:
      print traceback.format_exc(e)

  def do_exec(self,args):
    try:
      exec ' '.join(args)
    except Exception as e:
      print traceback.format_exc(e)

############################ </DEV>

  def __init__(self,fname):

    cmd.Cmd.__init__(self)
    self.prompt = Prompt(self.get_prompt)

    self.fname = fname
    self.char = None
    self.exported = {}
    self.modified = False
    if fname:
      self.do_load([fname])

  def get_prompt(self):
    if not self.char:
      return '[ --- none --- ] '
    c = self.char
    s = len(c.stats)
    b = len(c.bonuses)
    a = len([x for x in c.bonuses.values() if x.active])
    return '[ S:%-2s B:%2s/%-2s ] ' % (s,a,b)

  def parseline(self,line):
    args = line.split()
    return (args[0] if args else '',args[1:],line)

#  def precmd(self,line):
#    for c in ('EOF','','')

  def emptyline(self):
    pass

  def do_EOF(self,line):
    if self.overwrite():
      print ''
      return True

  def overwrite(self):
    if self.char is None or not self.modified:
      return True
    choice = raw_input('\nSave changes to current char? (Y/n/c): ').lower()
    if choice in ('y','yes'):
      return self.do_save([])==False
    if choice in ('n','no','cancel'):
      return True
    return False

  def default(self,line):
    args = line.split()
    if args[0] in self.exported:
      val = self.exported[args[0]]
      if isinstance(val,dict):
        if args[1] in val:
          result = val[args[1]](*args[2:])
          if result:
            print result
        else:
          print 'Unknown sub-command "%s"' % args[1]
      else:
        result = val(*args[1:])
        if result:
          print result
    else:
      print 'Unknown command "%s"' % args[0]

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

  def unplug(self):
    self.char = None
    self.exported = {}

  def do_new(self,args):
    if not self.overwrite():
      return
    args = args[0] if args else 'Pathfinder'
    self.plug(eval('char.%s()' % args))
    self.modified = True

  def do_load(self,args):
    if not self.overwrite():
      return
    if not os.path.isfile(args[0]):
      print 'Unable to read "%s"' % args[0]
      return
    try:
      with open(args[0],'rb') as f:
        self.plug(pickle.load(f))
        self.fname = args[0]
        self.modified = False
    except Exception:
      print 'Unable to unpickle "%s"' % args[0]

  def do_save(self,args):
    fname = self.fname if not args else ' '.join(args)
    if not fname:
      fname = raw_input('Enter a file name: ')
    try:
      with open(fname,'a') as f:
        pass
    except:
      print 'Unable to write "%s"' % fname
      return
    try:
      with open(fname,'wb') as f:
        pickle.dump(self.char,f,-1)
      self.fname = fname
      self.modified = False
      return False
    except:
      print 'Unable to pickle character'

if __name__=='__main__':

  args = sys.argv
  fname = None
  if len(args)>1:
    if os.path.isfile(args[1]):
      fname = args[1]
    else:
      print 'Unable to open "%s"' % args[1]
  main(fname)
