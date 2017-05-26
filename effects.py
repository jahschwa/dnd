#!/usr/bin/env python
#
# D&D status effect tracker
#
# Add effects and then iterate across rounds, minutes, or hours to track when
# they expire (also supports permanent effects)
#
# Joshua A Haas
# 2017/02/14

import sys,os,traceback
from bisect import bisect
from collections import OrderedDict
from ConfigParser import SafeConfigParser
from functools import total_ordering

from PyQt4 import QtGui,QtCore
from PyQt4.Qt import QApplication

# Custom file descriptor for use with SafeConfigParser to insert a dummy section
# (the library requires [Sections] in config file but I don't want any)
class FakeSecHead(object):
    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[dummy]\n'
    def readline(self):
        if self.sechead:
            try: 
                return self.sechead
            finally: 
                self.sechead = None
        else: 
            return self.fp.readline()

################################################################################
# Main
################################################################################

def main():
  app = QtGui.QApplication(sys.argv)
  chat = Tracker()
  sys.exit(app.exec_())

################################################################################
# Validator classes
################################################################################

class ValidBool(QtGui.QValidator):

  def validate(self,text,pos):
    """check for valid bool"""

    text = str(text)

    for s in ('true','false'):
      if s==text.lower():
        return (self.Acceptable,pos)
      if s.startswith(text.lower()):
        return (self.Intermediate,pos)

    return (self.Invalid,pos)

class ValidFile(QtGui.QValidator):

  def validate(self,text,pos):
    """check for valid filename"""

    text = str(text)

    if os.path.isfile(text) or text=='effects.state':
      return (self.Acceptable,pos)
    if not text or os.path.isdir(os.path.dirname(text)):
      return (self.Intermediate,pos)

    return (self.Invalid,pos)

################################################################################
# Qt Main Window
################################################################################

class Tracker(QtGui.QMainWindow):

  BUTTONS = OrderedDict([
    ('Advance',[('+1 round','round'),('+custom','custom')]),
    ('Effect',['new','link','edit','remove',('clear all','clear')]),
    ('State',['save',('save as','saveas'),'load','config'])
  ])

  DEFAULTS = OrderedDict([
    ('default_duration','5'),
    ('display_raw_rounds','false'),
    ('state_load_on_startup','true'),
    ('remember_last_file','true'),
    ('file_dialog_on_startup','false'),
    ('state_save_on_change','false'),
    ('clear_all_inc_infinite','true'),
    ('rounds_red','3'),
    ('rounds_yellow','10'),
    ('last_state_file','effects.state')
  ])

  VALIDATORS = {
    'default_duration':QtGui.QIntValidator(0,100),
    'display_raw_rounds':ValidBool(),
    'state_load_on_startup':ValidBool(),
    'remember_last_file':ValidBool(),
    'file_dialog_on_startup':ValidBool(),
    'state_save_on_change':ValidBool(),
    'clear_all_inc_infinite':ValidBool(),
    'rounds_red':QtGui.QIntValidator(0,1000000),
    'rounds_yellow':QtGui.QIntValidator(0,1000000),
    'last_state_file':ValidFile()
  }

  def __init__(self):

    super(Tracker,self).__init__()

    self.conf_file = 'effects.conf'
    self.current_file = 'effects.state'
    self.config_load()

    self.effects = []
    self.btns = {}
    self.changed = False

    self.initUI()
    self.center()
    self.show()

  def initUI(self):
    """create the main window UI including callbacks"""

    self.setWindowTitle('*unsaved')

    # create the main grid
    grid = QtGui.QGridLayout()
    grid.setSpacing(10)
    area = QtGui.QWidget(self)
    area.setLayout(grid)
    self.setCentralWidget(area)

    # add effects list
    self.effect_list = QtGui.QListWidget()
    grid.addWidget(self.effect_list,0,0)

    # add buttons
    vbox = QtGui.QVBoxLayout()
    vbox.setSpacing(10)
    area = QtGui.QWidget(area)
    area.setLayout(vbox)

    for (group_name,btn_names) in self.BUTTONS.items():
      (w,l) = self.make_box(group_name,area)
      for btn in btn_names:
        (name,func) = btn if isinstance(btn,tuple) else (btn,btn)
        self.make_button(l,name,func)
      vbox.addWidget(w)

    area.setFixedSize(area.sizeHint())
    grid.addWidget(area,0,1,QtCore.Qt.AlignTop)

    self.state_startup()

    self.setFocus()

  def make_box(self,name,area):
    """helper function to create a new groupbox and return the VBoxLayout"""

    w = QtGui.QGroupBox(name,area)
    l = QtGui.QVBoxLayout()
    w.setLayout(l)
    return (w,l)

  def make_button(self,grid,name,func):
    """helper function to add a button to the grid"""

    button = QtGui.QPushButton(name,self)
    button.clicked.connect(getattr(self,'btn_'+func))
    button.resize(button.sizeHint())
    grid.addWidget(button)
    self.btns[func] = button

  def closeEvent(self,event):
    """create an Are you sure? dialog"""

    # don't show the dialog if nothing has changed since last save
    if not self.changed:
      event.accept()
      return

    buttons = ( QtGui.QMessageBox.Save |
                QtGui.QMessageBox.Cancel |
                QtGui.QMessageBox.Discard )
    result = self.msg('You have unsaved changes.','Are you sure?',
        btns = buttons, default = QtGui.QMessageBox.Save)

    if result==QtGui.QMessageBox.Cancel:
      event.ignore()
      return
    if result==QtGui.QMessageBox.Save:
      self.state_save()
    event.accept()

    if self.opts['remember_last_file']=='true':
      self.opts['last_state_file'] = self.current_file
      self.config_save()

  def msg(self,text,title,detail=None,btns=None,default=None):
    """display a message box and return its result"""

    msgbox = QtGui.QMessageBox()
    msgbox.setText(text)
    msgbox.setWindowTitle(title)
    if detail:
      msgbox.setDetailedText(detail)
    if btns:
      msgbox.setStandardButtons(btns)
    if default:
      msgbox.setDefaultButton(default)
    return msgbox.exec_()

  def center(self):
    """center the window on the current monitor"""

    # http://stackoverflow.com/a/20244839/2258915

    fg = self.frameGeometry()
    cursor = QtGui.QApplication.desktop().cursor().pos()
    screen = QtGui.QApplication.desktop().screenNumber(cursor)
    cp = QtGui.QApplication.desktop().screenGeometry(screen).center()
    fg.moveCenter(cp)
    self.move(fg.topLeft())

  def config_load(self):
    """read options from config file or set defaults"""

    # start with defaults, if the file does not exist write the defaults
    self.opts = OrderedDict([(k,str(v)) for (k,v) in self.DEFAULTS.items()])
    if not os.path.isfile(self.conf_file):
      self.config_save()
      return

    # read options from the config file into a dict
    conf = SafeConfigParser()
    result = conf.readfp(FakeSecHead(open(self.conf_file)))
    opts = {x:y for (x,y) in conf.items('dummy')}
    for (k,v) in opts.items():
      if k!='last_state_file':
        opts[k] = v.lower()

    # update self.opts with options from the config file
    for opt in opts:
      if opt in self.opts:
        self.opts[opt] = opts[opt]

  def config_save(self):
    """save our current opts to the config file"""

    s = ''
    line = True
    for opt in self.opts:
      s += '%s = %s\n' % (opt,self.opts[opt])
    with open(self.conf_file,'w') as f:
      f.write(s)

  def state_load(self,fil=None):
    """load the state from the state file if it exists"""

    fil = (fil or self.current_file)
    if not os.path.isfile(fil):
      self.msg('File "%s" does not exist' % fil,'Error')
      return

    try:
      with open(fil,'r') as f:
        lines = [l.strip('\n\r') for l in f.readlines()]
      effects = []
      for l in lines:
        if not l:
          continue
        (name,dur,link) = l.split('\t')
        effects.append(Effect(name,dur,link,dur=='-1'))

    except Exception as e:
      self.msg('Unable to parse state file','Error',traceback.format_exc(e))
      return

    self.effect_clear()
    self.effect_add(effects,change=False)
    self.current_file = fil
    self.title_update()
    self.change(False)

  def state_save(self,fil=None):
    """save the state to the state file"""

    lines = []
    for effect in self.effects:
      link = effect.link or ''
      dur = -1 if effect.inf else effect.dur
      lines.append('%s\t%s\t%s\n' % (effect.name,dur,link))
    try:
      fil = fil or self.current_file
      with open(fil,'w') as f:
        f.writelines(lines)
      self.current_file = fil
      self.title_update()
      self.change(False)
    except:
      self.msg('Unable to write to file "%s"' % fil,'Permission Denied')

  def state_startup(self):
    """load state on startup if needed"""

    if self.opts['state_load_on_startup']=='true':
      self.current_file = self.opts['last_state_file']
      if self.opts['file_dialog_on_startup']=='true':
        self.current_file = str(QtGui.QFileDialog.getOpenFileName(self,'Load',
            os.path.dirname(os.path.realpath(self.current_file)),
            'Effect states (*.state);;All files (*.*)'))
      self.state_load()

  def effect_add(self,eff,update=True,change=True):
    """helper function for adding an effect"""

    if isinstance(eff,list):
      for e in eff:
        self.effect_add(e,False,False)
      self.effect_update()
      if change:
        self.change()

    else:
      ind = bisect(self.effects,eff)
      self.effects.insert(ind,eff)
      raw_rds = (self.opts['display_raw_rounds']=='true')
      self.effect_list.insertItem(ind,eff.to_str(raw_rds))
      self.effect_list.item(ind).setForeground(QtCore.Qt.darkGreen)

      if update:
        self.effect_update()
      if change:
        self.change()

  def effect_update(self):
    """iterate over effects, change colors, and notify for expirations"""

    dead = []
    for (i,effect) in enumerate(self.effects):
      text = effect.to_str(self.opts['display_raw_rounds']=='true')
      if effect.dur==0:
        dead.append(effect.name)
        self.effect_list.item(i).setForeground(QtCore.Qt.black)
        text = ' *** '+text
      else:
        if effect.inf:
          self.effect_list.item(i).setForeground(QtCore.Qt.darkGray)
        elif effect.dur<=int(self.opts['rounds_red']):
          self.effect_list.item(i).setForeground(QtCore.Qt.red)
        elif effect.dur<=int(self.opts['rounds_yellow']):
          self.effect_list.item(i).setForeground(QtCore.Qt.darkYellow)
      self.effect_list.item(i).setText(text)
    if dead:
      self.msg('Some effect(s) expired','Expired',detail='\n'.join(dead))
    for name in dead:
      self.effect_remove(name)

  def effect_remove(self,name):
    """helper function to remove effects"""

    ind = [i for (i,e) in enumerate(self.effects) if e.name==name][0]
    del self.effects[ind]
    self.effect_list.takeItem(ind)
    self.change()

  def effect_clear(self,force=False):
    """helper function to clear all effects"""

    for (name,inf) in [(e.name,e.inf) for e in self.effects]:
      if self.opts['clear_all_inc_infinite']=='false' and not force and inf:
        continue
      self.effect_remove(name)
    self.change()

  def effect_advance(self,rds):
    """helper function to advance all effects by rds"""

    if not self.effects:
      return
    for effect in self.effects:
      effect.advance(rds)
    self.effect_update()
    self.effect_list.setCurrentRow(-1)
    self.change()

  def change(self,new=True):
    """helper function to track changes since last save"""

    if self.changed==new:
      return
    if new and self.opts['state_save_on_change']=='true':
      self.state_save()
      return

    self.changed = new
    save_btn = self.btns['save']
    if new:
      save_btn.setText('SAVE')
      save_btn.setStyleSheet('QPushButton { color:red; }')
    else:
      save_btn.setText('save')
      save_btn.setStyleSheet(self.btns['load'].styleSheet())
    self.title_update()

  def title_update(self):
    """set the window title to the filename"""

    s = os.path.basename(self.current_file)
    if self.changed:
      s = '*'+s
    self.setWindowTitle(s)

  def btn_round(self):
    """advance by one round and update"""

    self.effect_advance(1)

  def btn_custom(self):
    """advance by a user specified amount and update"""

    if not self.effects:
      return
    d = AdvanceDialog(self)
    if d.exec_():
      rds = d.get()
      if rds:
        self.effect_advance(d.get())
      else:
        self.msg('Unable to advance: blank duration','Error')

  def btn_new(self):
    """add a new effect"""

    d = AddDialog(self)
    if d.exec_():
      e = d.get()
      if reduce(lambda a,b: a or e.name==b.name,self.effects,False):
        self.msg('Unable to add effect: duplicate name','Error')
      else:
        self.effect_add(e)

  def btn_link(self):
    """follow the selected effect's link or display the text"""

    ind = self.effect_list.currentRow()
    if ind==-1:
      return
    link = self.effects[ind].link
    if link and (link.startswith('http') or link.startswith('file')):
      QtGui.QDesktopServices.openUrl(QtCore.QUrl(link))
    else:
      self.msg(str(link),'Link Text')

  def btn_edit(self):
    """edit the contents of an effect"""

    ind = self.effect_list.currentRow()
    if ind==-1:
      return
    old = self.effects[ind]

    d = AddDialog(self,old)
    if d.exec_():
      new = d.get()
      effects = self.effects[:ind]+self.effects[ind+1:]
      if reduce(lambda a,b: a or new.name==b.name,effects,False):
        self.msg('Unable to edit effect: duplicate name','Error')
      else:
        self.effect_remove(old.name)
        self.effect_add(new)

  def btn_remove(self):
    """remove the selected effect"""

    ind = self.effect_list.currentRow()
    if ind>-1:
      self.effect_remove(self.effects[ind].name)

  def btn_clear(self):
    """clear all effects"""

    if not self.effects:
      return
    result = self.msg('Are you sure?','Clear All',
        btns = QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
        default = QtGui.QMessageBox.Cancel)
    if result==QtGui.QMessageBox.Ok:
      self.effect_clear()

  def btn_save(self):
    """save the state to disk"""

    self.state_save()

  def btn_saveas(self):
    """save the state to the specified file"""

    fil = str(QtGui.QFileDialog.getSaveFileName(self,'Save As',
        os.path.dirname(os.path.realpath(self.current_file)),
        'Effect states (*.state);;Text files (*.txt);;All files (*.*)'))
    if not fil:
      return

    if os.path.isfile(fil):
      result = self.msg('File exists; overwrite?','Save As',
        btns = QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
        default = QtGui.QMessageBox.Cancel)
      if result!=QtGui.QMessageBox.Ok:
        return

    self.state_save(fil)

  def btn_load(self):
    """load the state from disk"""

    fil = str(QtGui.QFileDialog.getOpenFileName(self,'Load State',
        os.path.dirname(os.path.realpath(self.current_file)),
        'Effect states (*.state);;All files (*.*)'))
    if not os.path.isfile(fil):
      return

    if self.changed:
      result = self.msg('Overwrite current state?','Load State',
        btns = QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
        default = QtGui.QMessageBox.Cancel)
      if result!=QtGui.QMessageBox.Ok:
        return

    self.effect_clear(force=True)
    self.state_load(fil)

  def btn_config(self):
    """edit config options"""

    OptsDialog(self)
    self.effect_update()

################################################################################
# Effect class
################################################################################

@total_ordering
class Effect(object):

  def __init__(self,name,dur=1,link=None,inf=False):

    self.name = name
    self.dur = int(dur) if (isinstance(dur,int) or dur.strip()) else None
    self.link = (link or None)
    self.inf = inf

  def advance(self,x):

    if not self.inf:
      self.dur = max(0,self.dur-x)

  def full_match(self,other):

    if not isinstance(other,Effect):
      return False
    return (self.name==other.name and
        self.dur==other.dur and
        self.link==other.link and
        self.inf==other.inf)

  def to_str(self,rds=False):

    link = ('+' if self.link else '-')

    if self.inf:
      dur = 'inf' if rds else '99:99.9'
      return '%s %s %s' % (dur,link,self.name)

    if rds:
      return '%s %s %s' % (self.dur,link,self.name)

    hr = self.dur/600
    mi = int(self.dur/10)%60
    rd = self.dur%10
    return '%.2d:%.2d.%.1d %s %s' % (hr,mi,rd,link,self.name)

  def __eq__(self,other):

    if not isinstance(other,Effect):
      return False
    return (self.inf and other.inf) or self.dur==other.dur

  def __lt__(self,other):

    if self.inf:
      return False
    if other.inf:
      return not self.inf
    return self.dur<other.dur

  def __str__(self):
    return self.to_str()

################################################################################
# Add dialog class
################################################################################

class AddDialog(QtGui.QDialog):

  def __init__(self,parent,effect=None):

    super(AddDialog,self).__init__(parent)

    self.effect = effect

    self.initUI()
    self.setModal(True)
    self.show()

  def initUI(self):

    grid = QtGui.QGridLayout()
    grid.setSpacing(10)
    self.setLayout(grid)

    grid.addWidget(QtGui.QLabel('Name',self),0,0)
    self.namebox = QtGui.QLineEdit(self)
    grid.addWidget(self.namebox,0,1,1,3)

    grid.addWidget(QtGui.QLabel('Duration',self),1,0)
    self.durbox = QtGui.QLineEdit(self.parent().opts['default_duration'],self)
    self.durbox.setValidator(QtGui.QIntValidator(1,1000000))
    grid.addWidget(self.durbox,1,1)
    self.unitbox = QtGui.QComboBox(self)
    for u in ('rds','min','x10 min','hrs'):
      self.unitbox.addItem(u)
    grid.addWidget(self.unitbox,1,2)
    self.infbox = QtGui.QCheckBox('Infinite',self)
    self.infbox.stateChanged.connect(self.toggle_inf)
    grid.addWidget(self.infbox,1,3)

    grid.addWidget(QtGui.QLabel('Link',self),2,0)
    self.linkbox = QtGui.QLineEdit(self)
    grid.addWidget(self.linkbox,2,1,1,3)

    self.make_button(grid,'OK',3,2,self.btn_ok)
    self.make_button(grid,'Cancel',3,3,self.btn_cancel)

    if self.effect:
      self.namebox.setText(self.effect.name)
      self.durbox.setText(str(self.effect.dur))
      if self.effect.inf:
        self.infbox.setChecked(True)
        self.toggle_inf(QtCore.Qt.Checked)
      self.linkbox.setText(self.effect.link or '')

    self.setFixedSize(self.sizeHint())
    self.setWindowTitle('%s Effect' % ('Edit' if self.effect else 'New'))

  def make_button(self,grid,name,x,y,func):

    button = QtGui.QPushButton(name,self)
    button.clicked.connect(func)
    button.resize(button.sizeHint())
    grid.addWidget(button,x,y)

  def toggle_inf(self,state):

    if state==QtCore.Qt.Checked:
      self.durbox.setEnabled(False)
      self.unitbox.setEnabled(False)
    elif state==QtCore.Qt.Unchecked:
      self.durbox.setEnabled(True)
      self.unitbox.setEnabled(True)

  def btn_ok(self):

    if self.validate():
      if self.get().full_match(self.effect):
        self.reject()
      self.accept()

  def btn_cancel(self):

    self.reject()

  def validate(self):
    """validate all options before saving"""

    text = []
    if not str(self.namebox.text()):
      text.append('Name cannot be blank')
    if not self.infbox.isChecked() and not str(self.durbox.text()):
      text.append('Invalid duration')

    if text:
      self.parent().msg(',\n'.join(text),'Error'+('s' if len(text)>1 else ''))
      return False
    return True

  def get(self):

    name = str(self.namebox.text())
    dur = int(self.durbox.text())*[1,10,100,600][self.unitbox.currentIndex()]
    link = str(self.linkbox.text())
    inf = self.infbox.isChecked()
    return Effect(name,dur,link,inf)

################################################################################
# Advance dialog class
################################################################################

class AdvanceDialog(QtGui.QDialog):

  def __init__(self,parent):

    super(AdvanceDialog,self).__init__(parent)
    self.initUI()
    self.setModal(True)
    self.show()

  def initUI(self):

    grid = QtGui.QGridLayout()
    grid.setSpacing(10)
    self.setLayout(grid)

    self.durbox = QtGui.QLineEdit('1',self)
    self.durbox.setValidator(QtGui.QIntValidator(1,1000000))
    grid.addWidget(self.durbox,0,0)

    self.unitbox = QtGui.QComboBox(self)
    for u in ('rds','min','hrs'):
      self.unitbox.addItem(u)
    grid.addWidget(self.unitbox,0,1)

    self.make_button(grid,'OK',1,0,self.accept)
    self.make_button(grid,'Cancel',1,1,self.reject)

    self.setFixedSize(self.sizeHint())
    self.setWindowTitle('Advance')

  def make_button(self,grid,name,x,y,func):

    button = QtGui.QPushButton(name,self)
    button.clicked.connect(func)
    button.resize(button.sizeHint())
    grid.addWidget(button,x,y)

  def get(self):
    return int(self.durbox.text() or 0)*[1,10,600][self.unitbox.currentIndex()]

################################################################################
# Options dialog class
################################################################################

class OptsDialog(QtGui.QDialog):

  def __init__(self,parent):
    
    super(OptsDialog,self).__init__(parent)
    self.initUI()
    self.setModal(True) # deny interaction with the main window until closed
    self.show()

  def initUI(self):
    """create labels and edit boxes"""

    # create grid layout
    grid = QtGui.QGridLayout()
    grid.setSpacing(10)
    self.setLayout(grid)

    # add QLabels and QLineEdits
    p = self.parent()
    for (row,opt) in enumerate(p.opts.keys()):
      grid.addWidget(QtGui.QLabel(opt,self),row,0)
      box = QtGui.QLineEdit(p.opts[opt],self)
      if opt in p.VALIDATORS:
        box.setValidator(p.VALIDATORS[opt])
      grid.addWidget(box,row,1)

    # add OK and Cancel buttons
    row += 1
    self.make_button(grid,'OK',row,0)
    self.make_button(grid,'Cancel',row,1)

    # disabled resizing and set name
    self.setFixedSize(self.sizeHint())
    self.setWindowTitle('Options')

  def make_button(self,grid,name,x,y):
    """helper function to add a button to the grid"""
    
    button = QtGui.QPushButton(name,self)
    button.clicked.connect(self.cb_button)
    button.resize(button.sizeHint())
    grid.addWidget(button,x,y)

  def cb_button(self):
    """catch button presses"""

    # only save config on 'OK' but close the dialog either way
    b = self.sender().text()
    if b=='OK' and self.validate():
      self.config_save()
      self.close()
    elif b=='Cancel':
      self.close()

  def validate(self):
    """validate all options before saving"""

    grid = self.layout()
    invalid = []
    for i in range(0,grid.rowCount()-1):
      opt = grid.itemAtPosition(i,0).widget().text()
      if not grid.itemAtPosition(i,1).widget().hasAcceptableInput():
        invalid.append(str(opt))
    if invalid:
      text = 'The values for the following are invalid:\n\n'+'\n'.join(invalid)
      self.parent().msg(text,'Error')
      return False
    return True

  def config_save(self):
    """save the user-entered config"""

    # we can access the values in the text boxes by getting them from the grid
    p = self.parent()
    grid = self.layout()

    # update the main window's 'opts' dictionary then call its config_save()
    for i in range(0,grid.rowCount()-1):
      opt = grid.itemAtPosition(i,0).widget().text()
      val = grid.itemAtPosition(i,1).widget().text()
      p.opts[str(opt)] = str(val)
    p.config_save()

################################################################################
# Main
################################################################################

if __name__ == '__main__':
  main()
