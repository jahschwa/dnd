from collections import OrderedDict
from functools import reduce

from dnd import util
from dnd.char_sheet.char import Character
from dnd.char_sheet.fields import *
from dnd.char_sheet.errors import *

# [TODO] level up wiz
# [TODO] multiclassing?
# [TODO] raise warning / limit skill ranks? _total_ranks stat?
# [TODO] conditional jump modifier based on move speed
# [TODO] craft, profession, perform
# [TODO] class skills
# [TODO] max_dex
# [TODO] consider using _base_reflex etc.

###############################################################################
# Pathfinder character class
#   - includes a setup wizard via the "wiz" command
#   - new class PathfinderSkill subclasses Stat
###############################################################################

class Pathfinder(Character):

  STATS = Character.STATS.copy()
  STATS.update([

  ('xp',0),('level',1),('hd','$level'),('caster_level','$level'),

  ('size',0),('legs',2),
  ('_size_index','4 if $size not in [-8,-4,-2,-1,0,1,2,4,8] else [-8,-4,-2,-1,0,1,2,4,8].index($size)'),

  ('strength',10),('dexterity',10),('constitution',10),
  ('intelligence',10),('wisdom',10),('charisma',10),
  ('str','int(($strength-10)/2)'),
  ('dex','int(($dexterity-10)/2)'),
  ('con','int(($constitution-10)/2)'),
  ('int','int(($intelligence-10)/2)'),
  ('wis','int(($wisdom-10)/2)'),
  ('cha','int(($charisma-10)/2)'),

  ('hit_die',0),('hp_max',0),('hp','$hp_max+$hd*($con-#con)'),('nonlethal',0),
  ('initiative','$dex'),('dr',0),('sr',0),('speed',30),

  ('armor_check',0),('_max_dex',99),('spell_fail',0),

  ('_ac_armor',0),('_ac_shield',0),('_ac_dex','min($dex,$_max_dex)'),
  ('_ac_nat',0),('_ac_deflect',0),('_ac_misc',0),
  ('ac','10+$_ac_armor+$_ac_shield+$_ac_dex-$size+$_ac_nat+$_ac_deflect+$_ac_misc'),
  ('ac_touch','10+$_ac_dex-$size+$_ac_deflect+$_ac_misc'),
  ('ac_ff','10+$_ac_armor+$_ac_shield-$size+$_ac_nat+$_ac_deflect+$_ac_misc'),

  ('fortitude','$con'),('reflex','$dex'),('will','$wis'),

  ('bab',0),('sr',0),('melee','$bab-$size+$str'),('ranged','$bab-$size+$dex'),

  ('cmb','$melee+2*$size'),
  ('cmd','10+$bab+$str+$_ac_dex+$_ac_deflect+$_ac_misc+$size'),

  ('acp','0'),

  ('_carry_size','([0.125,0.25,0.5,0.75,1,2,4,8,16] if $legs==2 else [0.25,0.5,0.75,1,1.5,3,6,12,24])[$_size_index]'),
  ('carry_heavy','$_carry_size*(10*$strength if $strength<11 else 2**int(($strength-11)/5)*[200,115,130,150,175][$strength%5])'),
  ('carry_light','int($carry_heavy/3)'),
  ('carry_medium','int(2*$carry_heavy/3)'),
  ('carry_lift_head','$carry_heavy'),
  ('carry_lift_ground','2*$carry_heavy'),
  ('carry_drag','5*$carry_heavy'),

  ('spell_mod',0),('spells_mod',0),('spell_dc','10+$spell_mod'),
  ('concentration','$caster_level+$spell_mod')

  ])

  SKILLS = OrderedDict([

  ('acrobatics','$dex'),('appraise','$int'),('bluff','$cha'),('climb','$str'),
  ('craft','$int'),('diplomacy','$cha'),('disable_device','$dex'),
  ('disguise','$cha'),('escape_artist','$dex'),('fly','$dex'),
  ('handle_animal','$cha'),('heal','$wis'),('intimidate','$cha'),

  ('knowledge_arcana','$int'),('knowledge_dungeoneering','$int'),
  ('knowledge_engineering','$int'),('knowledge_geography','$int'),
  ('knowledge_history','$int'),('knowledge_local','$int'),
  ('knowledge_nature','$int'),('knowledge_nobility','$int'),
  ('knowledge_planes','$int'),('knowledge_religion','$int'),

  ('linguisitics','$int'),('perception','$wis'),('perform','$cha'),
  ('profession','$wis'),('ride','$dex'),('sense_motive','$wis'),
  ('sleight_of_hand','$dex'),('spellcraft','$int'),('stealth','$dex'),
  ('survival','$wis'),('swim','$str'),('use_magic_device','$cha')

  ])

  SKILLS_TRAINED_ONLY = ['disable_device','handle_animal','knowledge',
      'linguisitics','profession','sleight_of_hand','spellcraft',
      'use_magic_device']
  SKILLS_TINY_DEX = ['climb', 'swim']

  TEXTS = Character.TEXTS.copy()
  TEXTS.update({'race':'','class':'','race_traits':'','xp_prog':'medium'})

  BONUS_TYPES = ('alchemical','armor','circumstance','competence','deflection',
      'dodge','enhancement','inherent','insight','luck','morale',
      'natural_armor','profane','racial','resistance','sacred','shield',
      'size','trait','penalty','none')
  BONUS_STACK = ('none','dodge','circumstance','racial','penalty')
  BONUS_PERM = ('inherent','racial','trait')

  AC_BONUS = {'armor':'_ac_armor','deflection':'_ac_deflect','dodge':'_ac_dex',
      'natural_armor':'_ac_nat','shield':'_ac_shield','size':'_ac_size'}

  ABILITIES = ['strength','dexterity','constitution',
      'intelligence','wisdom','charisma']
  SAVES = ['fortitude','reflex','will']

  XP = {
    'slow'   : [0,3,7.5,14,23,35,53,77,115,160,235,330,475,665,955,1350,1900,2700,3850,5350],
    'medium' : [0,2,5,9,15,23,35,51,75,105,155,220,315,445,635,890,1300,1800,2550,3600],
    'fast'   : [0,1.3,3.3,6,10,15,23,34,50,71,105,145,210,295,425,600,850,1200,1700,2400]
  }

  SIZE_NAMES = OrderedDict([
      ('f','fine'),
      ('d','diminutive'),
      ('t','tiny'),
      ('s','small'),
      ('m','medium'),
      ('l','large'),
      ('h','huge'),
      ('g','gargantuan'),
      ('c','colossal')
  ])
  SIZES = [8,4,2,1,0,-1,-2,-4,-8]

  RACE_INDEX = ['size','speed','abilities','bonuses','traits','manual']
  RACE_INFO = {
      'dwarf':['m',20,'245',
          [   ['defensive_training',4,'ac','dodge','vs subtype(giant)'],
              ['hardy',2,SAVES,'vs poison,spells,spell-like-abilities'],
              ['stability',4,'cmd','vs bull-rush,trip while standing on ground'],
              ['greed',2,'appraise','on non-magical items containing gems/metals'],
              ['stonecunning',2,'perception','none','to notice unusual stonework'],
              ['hatred',1,['melee','ranged'],'vs subtype(orc,goblinoid)']
          ],
          [   'darkvision 60ft',
              'weapons: battleaxe,heavy_pick,warhammer',
              'auto perception check within 10ft of unusual stonework'
          ],
          ['speed never reduced by armor/encumbrance']
      ],
      'elf':['m',30,'132',
          [   ['immunities',2,SAVES,'vs enchantment spells/effects'],
              ['keen_senses',2,'perception'],
              ['magic',2,'caster_level','to overcome spell resistance'],
              ['magic_items',2,'spellcraft','to identify magic items']
          ],
          [   'immune to magic sleep',
              'low-light-vision',
              'weapons: longbow,longsword,rapier,shortbow'
          ],
          []
      ],
      'gnome':['s',20,'250',
          [   ['defensive_training',4,'ac','dodge','vs subtype(giant)'],
              ['illusion_resistance',2,SAVES,'vs illusion spells/effects'],
              ['keen_senses',2,'perception'],
              ['magic',1,'spell_dc','none','for illusion spells'],
              ['hatred',1,['melee','ranged'],'none','vs subtype(reptilian,goblinoid)']
          ],
          ['low-light-vision'],
          ['+2 on 1 craft or profession','gnome_magic']
      ],
      'halfelf': ['m',30, None,
          [   ['immunities',2,SAVES,'vs enchantment spells/effects'],
              ['keen_senses',2,'perception'],
          ],
          [   'immune to magic sleep',
              'low-light-vision',
              'count as both elves and humans',
              'choose 2 favored classes'
          ],
          ['skill focus at 1st level']
      ],
      'halforc': ['m',30, None,
          [['intimidating',2,'intimidate']],
          ['darkvision 60ft','count as both orcs and humans'],
          ['ferocity 1/day for 1 round']
      ],
      'halfling': ['s',20,'150',
          [   ['fearless',2,SAVES,'vs fear'],
              ['luck',1,SAVES],
              ['sure_footed',2,['acrobatics','climb']],
              ['keen_senses',2,'perception']
          ],
          ['weapons: sling'],
          []
      ],
      'human':    ['m',30, None,
          [],
          ['+1 skill rank per level'],
          ['bonus feat at 1st level']
      ]
  }

  CLASS_INDEX = ['hd','skills','bab','saves','cast_mod']
  CLASS_INFO = {
      'barbarian': [12,'10011000001010000001000010010000110','1.00','100',None],
      'bard':      [8, '11111101100011111111111111101111001','0.75','011','cha'],
      'cleric':    [8, '01001100000101000100111100101010000','0.75','101','wis'],
      'druid':     [8, '00011000011100001001000010110010110','0.75','101','wis'],
      'fighter':   [10,'00011000001010110000000000110000110','1.00','100',None],
      'monk':      [8, '10011000100010000100001011111001010','0.75','111',None],
      'paladin':   [10,'00001100001100000000101000111010000','1.00','101','cha'],
      'ranger':    [10,'00011000001110101001000010110011110','1.00','110','wis'],
      'rogue':     [8, '11111111100010100010000111101101011','0.75','010',None],
      'sorcerer':  [6, '01101000010011000000000000100010001','0.50','001','cha'],
      'wizard':    [6, '01001000010001111111111100100010000','0.50','001','int'],

      'alchemist':   [8, '01000010010101000001000010100110101','0.75','110','int'],
      'cavalier':    [10,'00111100001010000000000000111000010','1.00','100',None],
      'gunslinger':  [10,'10111000001110010010000010110100110','1.00','110',None],
      'inquisitor':  [8, '00111101000111100001011010111011110','0.75','101','wis'],
      'magus':       [8, '00011000010011100000010000110010011','0.75','101','int'],
      'oracle':      [8, '00001100000100000100011000101010000','0.75','001','cha'],
      'summoner':    [8, '00001000011000000000000100110010001','0.75','001','cha'],
      'vigilante':   [8, '11111111100010110010000011111101111','0.75','011',None],
      'witch':       [6, '00001000010111000101010000100010001','0.50','011','int'],

      'arcane archer':         [10,'00000000000000000000000010010001100','1.00','332',None],
      'arcane trickster':      [6, '11110111100001111111111010001111010','0.50','233',None],
      'assassin':              [8, '10110111100010000000000110001101011','0.75','232',None],
      'dragon disciple':       [12,'00000100110001111111111010000010000','1.00','323',None],
      'duelist':               [10,'10100000100000000000000011001000000','1.00','232',None],
      'eldritch knight':       [10,'00010000000001000000100100011010010','1.00','322',None],
      'loremaster':            [6, '01000100001101111111111101000010001','0.50','223',None],
      'mystic theurge':        [6, '00000000000001000000001000001010000','0.50','223',None],
      'pathfinder chronicler': [8, '01100101100011111111111111011100101','0.75','233',None],
      'shadowdancer':          [8, '10100101100000000000000011000101000','0.75','232',None]
  }

  CLASS_SAVES = ['int(x/3)','2+int(x/2)','int((x+1)/3)','1+int((x-1)/2)']

  # @param args (list) passed to Character
  # @param kwargs (dict) passed to Character
  def __init__(self,*args,**kwargs):

    super(Pathfinder,self).__init__(*args,**kwargs)
    self.export += ['dmg','heal','skill','wiz','xp']

  # include skills in the setup method
  # see Character._setup()
  def _setup(self,ignore_dupes=False):

    super(Pathfinder,self)._setup(ignore_dupes)
    for (name,formula) in self.SKILLS.items():
      if name in self.SKILLS_TINY_DEX:
        formula = '($str if $size>-2 else $dex)'
      skill = PathfinderSkill(name,formula)
      try:
        self._add_stat(skill)
      except DuplicateError:
        if ignore_dupes:
          pass
        else:
          raise

  # include hp, status, ac
  # @return (str)
  def _get_prompt(self):
    return ('[ %s   %s   AC/To/FF: %s/%s/%s ]\n \___ ' % (
        self._get_name(),
        self._health(),
        self.stats['ac'].value,
        self.stats['ac_touch'].value,
        self.stats['ac_ff'].value
    ))

  # @return (int) our maximum hp (including bonuses except for _damage)
  def _max_hp(self):

    hp = self.stats['hp'].value
    if '_damage' not in self.bonuses:
      return hp
    return hp-self.bonuses['_damage'].value

  # @return (5-tuple)
  #   #0 (int) current hp
  #   #1 (int) max hp
  #   #2 (int) nonlethal damage
  #   #3 (int) the hp value when we die
  #   #4 (str) one of: up,DEAD,DYING,STAGGERED,UNCON
  def _get_status(self):

    current = self.stats['hp'].value
    max_hp = self._max_hp()
    nonlethal = self.stats['nonlethal'].value
    death = -self.stats['constitution'].value

    status = 'up'
    if current<=death:
      status = 'DEAD'
    elif current<0:
      status = 'DYING'
    elif current==0:
      status = 'STAGGERED'
    elif nonlethal>=current:
      status = 'UNCON'

    return (current,max_hp,nonlethal,death,status)

  # @return (str) hp and status info
  def _health(self):

    (current,max_hp,nonlethal,death,status) = self._get_status()
    non = '' if nonlethal==0 else '   Nonlethal: %s' % nonlethal
    death = '' if current>0 else '   Death: %s' % death
    status = '' if status=='up' else '   %s' % status
    return 'HP: %s/%s%s%s%s' % (current,max_hp,non,death,status)

  # set our size modifier and text
  # @param size (str) first letter or whole word of the standard sizes:
  #   fine,diminutive,tiny,small,medium,large,huge,gargantuan,colossal
  def _set_size(self,size):

    size = size[0].lower()
    i = list(self.SIZE_NAMES.keys()).index(size)
    self.set_stat('size',self.SIZES[i],self.SIZE_NAMES[size])

  # if None, use the values from this Character
  # @param xp (int) [None] amount of experience
  # @param prog (str) [None] level progression, one of [s,m,f]
  # @return (int) 
  def _calc_lvl(self,xp=None,prog=None):

    if xp is None:
      xp = self.stats['xp'].value
    if prog is None:
      prog = self.texts['xp_prog'].text

    if xp==0:
      return 1
    for (l,x) in enumerate(self.XP[prog]):
      if xp<int(1000*x):
        return l
    return 20

###############################################################################
# User commands
###############################################################################

  # [TODO] consider making massive damage an Event for consistency
  def dmg(self,damage,nonlethal=False):
    """
    take damage and update HP
      - damage (int) amount of damage to take (positive)
      - [nonlethal = False] (bool)
    """

    damage = int(damage)
    if damage<=0:
      raise ValueError('damage must be > 0')

    if nonlethal:
      self.set_stat('nonlethal',self.stats['nonlethal'].value+damage)
    else:
      if '_damage' in self.bonuses:
        self.set_bonus('_damage',self.bonuses['_damage'].value-damage)
      else:
        self.add_bonus('_damage',-damage,'hp')
      if damage>=50 and damage>=int(self._max_hp()/2):
        print('!!! Massive damage')

  def heal(self,damage):
    """
    heal damage and update HP
      - damage (int) amount of damage to heal (positive)
    """

    damage = int(damage)
    if damage<=0:
      raise ValueError('healing must be > 0')

    nonlethal = min(damage,self.stats['nonlethal'].value)
    try:
      current = -self.bonuses['_damage'].value
    except KeyError:
      current = 0
    damage = min(damage,current)

    if '_damage' in self.bonuses and damage:
      self.set_bonus('_damage',self.bonuses['_damage'].value+damage)
      if self.bonuses['_damage'].value==0:
        self.del_bonus('_damage')
    if nonlethal:
      self.set_stat('nonlethal',self.stats['nonlethal'].value-nonlethal)

  def skill(self,action='info',name=None,value=0):
    """
    manage skills
      - action (string) see below
      - [name = None] (string,list) the skill(s) to modify
        - leaving this field blank acts on all skills
      - [value = 0] (object)

    actions:
      - info [value = UNUSED] give some quick stats
      - list [value = None] show summary text
      - rank [value = 0] set skill ranks
      - class [value = UNUSED] set as class skills
      - unclass [value = UNUSED] set as not class skills
    """

    actions = ['info','list','rank','class','unclass']
    if action not in actions:
      raise ValueError('invalid sub-command "%s"' % action)

    name = name or list(self.SKILLS.keys())
    if not isinstance(name,list):
      name = [name]
    if action=='info':
      name = ['info']

    if action=='info':
      def func(name):
        skills = [x for x in self.stats.values()
            if isinstance(x,PathfinderSkill)]
        clas = reduce(lambda a,b: a+b.class_skill,skills,0)
        ranks = reduce(lambda a,b: a+b.ranks,skills,0)
        return '%s class skills\n%s ranks' % (clas,ranks)

    elif action=='list':
      func = lambda name: self.stats[name].str_search()

    elif action=='rank':
      func = lambda name: self.stats[name].set_ranks(int(value))

    elif action=='class':
      func = lambda name: self.stats[name].set_cskill()

    elif action=='unclass':
      func = lambda name: self.stats[name].set_cskill(False)

    for n in name:
      try:
        result = func(n)
      except Exception as e:
        result = '*** %s (%s) %s' % (e.__class__.__name__,n,e.args[0])
      if result:
        print(result)

  def xp(self,action='info',value=0):
    """
    manage XP
      - action (string) see below
      - [value = 0] (int)
    
    actions:
      - info [value = UNUSED] show xp/level info
      - add [value = 0] gain experience
    """

    actions = ['info','add']
    if action not in actions:
      raise ValueError('invalid sub-command "%s"' % action)
    
    if action=='info':
      xp = self.stats['xp'].value
      lvl = self.stats['level'].value
      expected = self._calc_lvl()
      if expected!=lvl:
        print('### %s XP should be Lvl %s but our level is set to %s' %
            (util.group(xp),expected,lvl))
      if expected==20:
        return '%s / Lvl 20' % util.group(xp)
      xp_next = int(1000*self.XP[self.texts['xp_prog'].text][expected])
      return ('%s / Lvl %s   + %s   = %s / Lvl %s' %
          (util.group(xp),expected,xp_next-xp,xp_next,expected+1))

    elif action=='add':
      gained = int(value)
      if gained<=0:
        raise ValueError('XP value must be > 0')
      old = self.stats['level'].value
      self.set_stat('xp',self.stats['xp'].value+gained)
      new = self._calc_lvl()
      if new>old:
        print('### Level up: %s --> %s' % (old,new))
        self.set_stat('level',new)
      return self.xp()

###############################################################################
# Overrides
###############################################################################

  def _add_bonus(self,bonus):

    bonus.stats = [
        (self.AC_BONUS.get(bonus.typ,'_ac_misc') if s=='ac' else s)
        for s in bonus.stats
    ]
    super(Pathfinder,self)._add_bonus(bonus)

###############################################################################
# Setup wizard
###############################################################################

  def wiz(self,action='help'):
    """
    character setup wizard for some automation
      - action (string) see below

    actions:
      - all [N/A] execute each [ALL] action below in order
      - level [ALL] set character level
      - race [ALL] set race and add racial bonuses
      - class [ALL] set class, some stats, and class skills
      - abilities [ALL] set ability scores and racial adjustments
      - hp [ALL] set hit points
      - skill [ALL] set skill ranks
      - size [ONE] set size (e.g. medium)
      - class_skill [ONE] set class skills

    special inputs:
      - skip - for the 'all' action, skip the current sub-action
      - quit - exit the wizard making no further changes
    """

    actions = ['level','race','class','abilities','hp','skill']
    standalone = ['size','class_skill']
    if action not in actions+standalone and action not in ('help','all'):
      raise ValueError('invalid sub-command "%s"' % action)

    if action=='help':
      print('(wiz) [all] (%s)' % ('|'.join(sorted(actions+standalone))))

    else:
      actions = actions if action=='all' else [action]
      try:
        for action in actions:
          action = getattr(self,'_wiz_'+action)
          if len(actions)>1:
            print('\n=== %s' % action.__doc__)
          try:
            action()
          except UserSkipException:
            continue
      except UserQuitException:
        pass

  def _wiz_level(self):
    """Character level"""

    prog = self._input(
        'Enter XP progression (s/M/f)',
        valid = lambda x: x[0] in [x[0] for x in self.XP]
    ) or 'medium'
    prog = [k for k in self.XP if k.startswith(prog)][0]
    self.set_text('xp_prog',prog)

    level = self._input(
        'Enter level (%s)' % self.stats['level'].value,
        parse = int,
        valid = lambda x: x>0
    )
    if level:
      self.set_stat('level',level)
      prog = self.texts['xp_prog'].text
      xp = int(1000*self.XP[prog][level-1])
      self.set_stat('xp',xp)
      print('current xp: %s' % util.group(xp))

  def _wiz_race(self):
    """Race"""

    if self.texts['race'].text:
      print("+++ WARNING: if you've already run this command don't re-run it")

    race = self._input(
        'Enter race name',
        parse = lambda x: x.replace('-','').replace('_',''),
        valid = lambda x: x in self.RACE_INFO,
        blank = False
    )
    self.set_text('race',race)
    info = self.RACE_INFO[race]

    size = info[self.RACE_INDEX.index('size')]
    self._set_size(size)

    speed = info[self.RACE_INDEX.index('speed')]
    self.set_stat('speed',speed)

    bonuses = info[self.RACE_INDEX.index('bonuses')]
    if len(bonuses):
      print('--- racial bonuses')
    for bonus in bonuses:
      args = bonus[:3]+['racial']
      args[0] = '%s_%s' % (race,args[0])
      while len(bonus)>3:
        s = bonus.pop()
        if s in self.BONUS_TYPES:
          args[3] = s
        else:
          args += [s]
      self.add_bonus(*args)
      print('  %s' % self.bonuses[args[0]]._str())

    traits = info[self.RACE_INDEX.index('traits')]
    if traits:
      self.set_text('race_traits','\n'.join(traits))
      print('--- all text race_traits')
      for t in traits:
        print('  %s' % t)

    manual = info[self.RACE_INDEX.index('manual')]
    for s in manual:
      print('+++ NOTE: %s' % s)

  def _wiz_class(self):
    """Class skills, BAB, Saves"""

    if self.texts['class'].text:
      print("+++ WARNING: if you've already run this command don't re-run it")

    clas = self._input(
        'Enter class name',
        valid = lambda x: x in self.CLASS_INFO,
        blank = False
    )
    self.set_text('class',clas)
    info = self.CLASS_INFO[clas]

    hd = info[self.CLASS_INDEX.index('hd')]
    self.set_stat('hit_die',hd)
    print('hit die: d%s' % hd)

    names = list(self.SKILLS.keys())
    one_hot = info[self.CLASS_INDEX.index('skills')]
    skills = []
    for (i,x) in enumerate(one_hot):
      if x=='1':
        skill = names[i]
        skills.append(skill)
        self.stat[skill].set_cskill()
    print('class skills: %s' % ','.join(skills))

    prog = info[self.CLASS_INDEX.index('bab')]
    self.set_stat('bab','int(%s*$level)' % prog)
    print('bab progression: %s' % prog)

    mods = ('con','dex','wis')
    progs = info[self.CLASS_INDEX.index('saves')]
    good = []
    for (save,mod,prog) in zip(self.SAVES,mods,progs):
      prog = int(prog)
      if prog in (1,3):
        good.append(save)
      base = self.CLASS_SAVES[prog].replace('x','$level')
      new = '$%s+%s' % (mod,base)
      self.set_stat(save,new,force=True)
    print('good saves: %s' % ','.join(good))

    mod = info[self.CLASS_INDEX.index('cast_mod')]
    if mod:
      self.set_stat('spell_mod','$'+mod)
      self.set_stat('spells_mod','#'+mod)
      print('casting mod: %s' % mod)

  def _wiz_abilities(self):
    """Ability scores"""

    self._inputs(
        [(  '%s (%s)' % (a,self.stats[a].normal),
            a,
            lambda k,v:self.set_stat(k,str(v))
        ) for a in self.ABILITIES],
        parse = int,
        valid = lambda x: x>=0
    )

    race = self.texts['race'].text
    if race and self._yn('Adjust for %s' % race):
      info = self.RACE_INFO[race]
      abilities = info[self.RACE_INDEX.index('abilities')]
      for (i,a) in enumerate(abilities):
        a = self.ABILITIES[int(a)]
        adjust = (-2 if i==2 else 2)
        new = self.stats[a].value+adjust
        self.set_stat(a,new)
        print('%s%s %s' % ('+' if adjust>0 else '',adjust,a))

  def _wiz_hp(self):
    """Hitpoints"""

    hp = self._input(
        'Maximum HP',
        parse = int,
        valid = lambda x: x>0
    )
    self.set_stat('hp_max',hp)

  def _wiz_skill(self):
    """Skill ranks"""

    print('+++ Max ranks: %s' % self.stats['level'].value)
    self._inputs(
        [(  '%s (%s)' % (s,self.stats[s].ranks),
            s,
            lambda k,v:self.stats[k].set_ranks(v)
        ) for s in self.SKILLS],
        parse = int,
        valid = lambda x: x>=0 and x<=self.stats['level'].value
    )

  def _wiz_size(self):
    """Size"""

    size = self._input(
        'Enter size',
        valid = lambda x: x[0] in self.SIZE_NAMES.keys()
    )
    self._set_size(size)

  def _wiz_class_skill(self):
    """Class skills"""

    self._yns(
        [(  '%s (%s)' % (s,'ny'[self.stats[s].class_skill]),
            s,
            lambda k,v:self.stats[k].set_cskill(v)
        ) for s in self.SKILLS]
    )

###############################################################################
# PathfinderSkill class
#   - subclasses Stat
###############################################################################

class PathfinderSkill(Stat):

  FIELDS = OrderedDict(
      [(k,v) for (k,v) in Stat.FIELDS.items()] +
      [('ranks',int),('class_skill',bool)]
  )

  # the first 6 args get passed to Stat
  # @param ranks (int) [0] skill ranks
  # @param class_skill (bool) [False]
  def __init__(self,*args,**kwargs):

    mine = list(args)[6:]
    if mine:
      self.ranks = mine.pop(0)
    else:
      self.ranks = kwargs.pop('ranks',0)
    if mine:
      self.class_skill = mine.pop(0)
    else:
      self.class_skill = kwargs.pop('clas',False)

    # Stat.__init__() with correct args
    super(PathfinderSkill,self).__init__(*args[:6],**kwargs)

    f = '+@ranks+(3 if @class_skill and @ranks else 0)'
    if '$dex' in self.original or '$str' in self.original:
      f += '+${acp}'

    # we need a check here so we don't double up on the +3 class skills when
    # loading from a file
    # [TODO] consider a cleaner way of controlling this
    if f not in self.formula:
      self.set_formula(self.formula+f)

    self.trained_only = False

    # needed for Stat.copy()
    self.COPY += ['ranks','class_skill']

  # @param new (bool) [True]
  def set_cskill(self,new=True):

    self.class_skill = new
    self.calc()

  # @param value (int)
  # @raise TypeError on value
  # @raise ValueError if value<0 or value>level
  def set_ranks(self,value):

    if not isinstance(value,int):
      raise TypeError('parameter "value" must be int')

    if value<0:
      raise ValueError('ranks must be >= 0')

    level = self.char.stats['level'].value
    if value>level:
      raise ValueError('ranks must be <= level=%s' % level)

    self.ranks = value
    self.calc()

  # @param char (Character)
  def plug(self,char):

    super(PathfinderSkill,self).plug(char)

    # determine if we're trained only or not
    for skill in self.char.SKILLS_TRAINED_ONLY:
      if self.name.startswith(skill):
        self.trained_only = True
        break

  # looks like: sc!
  #   s (type) this is a skill
  #   c (class_skill)
  #   ! OR t (trained_only) based on ranks>0
  # @return (str)
  def _str_flags(self):

    cs = '-c'[self.class_skill]
    tr = ['-!'[self.trained_only],'t'][self.ranks>0]
    return 's%s%s' % (cs,tr)

  # @return (str)
  def str_all(self):

    s = super(PathfinderSkill,self).str_all()

    l = ['  ranks | %s' % self.ranks]
    l.append(' cskill | %s' % self.class_skill)
    l.append('trained | %s' % ['anyone','only'][self.trained_only])

    return s+'\n'+'\n'.join(l)
