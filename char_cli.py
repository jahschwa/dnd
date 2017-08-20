#!/usr/bin/env python

# ===== WORKING EXAMPLES =====
#
# >>> new
# >>> set stat dexterity 17
# >>> get stat ac
# ac = 13
#
# >>> g s ac
# ac = 13
#
# >>> add bonus mage_armor 4 ac_armor armor
# >>> get stat ac,ff,touch
# ac = 17
# ff = 14
# touch = 13
#
# >>> off mage_armor
# >>> get stat ac,ff,touch
# ac = 13
# ff = 10
# touch = 13
#
# >>> all bonus mage_armor
#  value | 4
# active | False
#   type | armor
# revert | change
#  stats | ac_armor
#   text | 
#
# ===== PLANNED FOR THE FUTURE =====
#
# >>> get ac,ff,touch with mage_armor
# ac = 17
# ff = 14
# touch = 13
#
# >>> get stat ac,ff,touch
# ac = 13
# ff = 10
# touch = 13

# ===== QUICK COMMAND LISTING =====
#
# implemented types: stat bonus
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

import sys,os,pickle,cmd,inspect,traceback

import char

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

  def do_eval(self,args):
    try:
      print eval(' '.join(args))
    except:
      print traceback.format_exc()

  def do_exec(self,args):
    try:
      exec ' '.join(args)
    except:
      print traceback.format_exc()

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

  def emptyline(self):
    pass

  def postcmd(self,stop,line):
    print ''
    return stop

  def do_EOF(self,line):
    if self.overwrite():
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
    args = [a.split(',') if ',' in a else a for a in line.split()]
    if args[0] in self.exported:
      val = self.exported[args[0]]
      if isinstance(val,dict):
        if args[1] in val:
          (func,args) = (val[args[1]],args[2:])
        else:
          print 'Unknown sub-command "%s"' % args[1]
      else:
        (func,args) = (val,args[1:])
    else:
      print 'Unknown command "%s"' % args[0]
      return

    try:
      result = func(*args)
    except:
      print '*** '+traceback.format_exc().split('\n')[-2]
      return
    if result:
      print result

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
