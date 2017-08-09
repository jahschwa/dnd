#!/usr/bin/env python

import sys,os,pickle,cmd

import char

def main(fname):

  char = None
  if fname:
    with open(fname,'rb') as f:
      char = pickle.load(f)

  cli = CLI(char)
  run = True
  while run:
    try:
      cli.cmdloop()
      run = False
    except KeyboardInterrupt:
      print 'use Ctrl+D / EOF to exit'
      pass

class CLI(cmd.Cmd):

############################

  def do_echo(self,args):
    print args

  def do_eval(self,args):
    print eval(' '.join(args))

  def do_exec(self,args):
    exec ' '.join(args)

############################

  def __init__(self,char):

    cmd.Cmd.__init__(self)
    self.prompt = '> '

    self.char = char

  def parseline(self,line):
    args = line.split()
    return (args[0] if args else '',args[1:],line)

  def emptyline(self):
    sys.stdout.write('')

  def do_EOF(self,line):
    return True

  def do_new(self,args):
    args = args[0] if args else 'Pathfinder'
    self.char = eval('char.%s()' % args)

if __name__=='__main__':

  args = sys.argv
  fname = None
  if len(args)>1:
    if os.path.isfile(args[1]):
      fname = args[1]
    else:
      print 'Unable to open "%s"' % args[1]
  main(fname)
