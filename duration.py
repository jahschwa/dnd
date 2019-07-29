###############################################################################
# Duration class
#   - tracks a duration e.g. 1 round, 2 hours, 5 days
#   - can also be infinite
#   - can be based on $level or $caster_level e.g. 1/CL 1mi/2CL
###############################################################################

class Duration(object):

  INF = -1
  INF_NAMES = (None,'inf','infinity','infinite','perm','permanent','forever')
  EXP = 0
  EXP_NAMES = ('exp','expire','expired','inactive','off')

  UNITS = {
      ('','r','rd','rds','rnd','rnds','round','rounds') : 1,
      ('m','mi','min','mins','minute','minutes') : 10,
      ('h','hr','hrs','hour','hours') : 600,
      ('d','day','days') : 14400,
      ('y','yr','yrs','year','years') : 5256000,
      ('l','lvl','level') : '$level',
      ('cl','clvl','caster','casterlvl','casterlevel') : '$caster_level'
  }

  NAMES = [(5256000,'yr'),(14400,'day'),(600,'hr'),(10,'min'),(1,'rd')]

  # @param s (str)
  # @return (bool) whether the input string is an int
  @staticmethod
  def is_int(s):

    try:
      int(s)
      return True
    except:
      return False

  # @param s (str) unit name
  # @return (int) the corresponding multiplier for conversion to rounds
  @staticmethod
  def get_mult(s):

    for (names,mult) in Duration.UNITS.items():
      if s in names:
        return mult

    raise KeyError('unknown unit "%s"' % s)

  # @param s (str) one duration text
  # @return (2-tuple)
  #   #0 (str) the number
  #   #1 (str) unit
  @staticmethod
  def split_unit(s):

    i = 0
    while i<len(s) and Duration.is_int(s[i]):
      i += 1
    return (s[:i] or '1',s[i:])

  # @param s (str,int) full duration e.g. 1+1/CL
  # @return (str) input converted to valid python expression to be eval()
  @staticmethod
  def to_rds(s):

    if isinstance(s,int):
      return str(s)

    if isinstance(s,str):
      s = s.lower().replace(' ','').replace('_','')
    if s in Duration.INF_NAMES:
      return str(Duration.INF)
    if s in Duration.EXP_NAMES:
      return str(Duration.EXP)

    durs = s.split('+')

    rds = []
    for dur in durs:

      if dur.count('/')>1:
        raise ValueError('too many / in "%s"' % dur)

      dur = dur.split('/')
      (num,unit) = Duration.split_unit(dur[0])
      s = '%s*%s' % (num,Duration.get_mult(unit))

      if len(dur)>1:
        (num,stat) = Duration.split_unit(dur[1])
        s += '*max(1,int(%s/%s))' % (Duration.get_mult(stat),num)

      rds.append(s)

    return '+'.join(rds)

  # @param s (str,int,Duration) text to parse
  # @param char (Character)
  # @return (int) number of rounds
  # @raise ValueError if we need a Character but don't have one
  @staticmethod
  def parse(s,char):

    if isinstance(s,Duration):
      return (str(s),s.rounds)
    s = Duration.to_rds(s)

    # expand $level and $caster_level
    for unit in Duration.UNITS.values():
      if isinstance(unit,str) and unit.startswith('$'):
        s = s.replace(unit,'char.stats["%s"].value' % unit[1:])
    if 'char.stats' in s and not char:
      raise ValueError('string references Stats but missing Character')

    return (s,eval(s))

  # @param dur (str,int) [None] the duration text to parse (None = infinite)
  # @param char (Character) [None]
  def __init__(self,dur=None,char=None):

    (self.raw,self.original) = Duration.parse(dur,char)
    self.rounds = self.original
    self.char = char

  # @param dur (int,Duration) [1] value to subtract from remaining time
  # @return (bool) True if this Duration has expired
  # @raise TypeErrpr on dur
  def advance(self,dur=1):

    if isinstance(dur,Duration):
      dur = dur.rounds
    elif not isinstance(dur,int):
      raise TypeError('invalid type "%s"' % dur.__class__.__name__)

    if self.rounds==Duration.INF:
      return False
    if dur==Duration.INF:
      dur = self.rounds

    self.rounds = max(0,self.rounds-dur)
    return self.is_expired()

  # @return (bool) if we're expired
  def is_expired(self):
    return self.rounds==0

  # reset this duration back to its original value
  def reset(self):
    self.rounds = self.original

  # expire ourself
  def expire(self):
    self.rounds = 0

  # @return (Duration) time elapsed since creation (e.g. via advance() calls)
  def elapsed(self):
    return Duration(self.original)-self

  # @return (Duration)
  def copy(self):

    new = Duration()
    for var in ('raw','original','rounds','char'):
      setattr(new,var,getattr(self,var))
    return new

  # @param other (object)
  # @return (bool)
  def __eq__(self,other):

    if isinstance(other,int):
      return self.rounds==other
    elif isinstance(other,Duration):
      return self.rounds==other.rounds
    return NotImplemented

  def __lt__(self,other):

    if isinstance(other,int):
      return self.rounds<other
    elif isinstance(other,Duration):
      return self.rounds<other.rounds
    return NotImplemented

  def __add__(self,other):

    if isinstance(other,int):
      other = Duration(other)
    if not isinstance(other,Duration):
      return NotImplemented
    
    new = self.copy()
    if self.rounds==Duration.INF or other.rounds==Duration.INF:
      new.rounds = Duration.INF
    else:
      new.rounds = self.rounds+other.rounds
    return new
  
  def __radd__(self,other):
    return self.__add__(other)
  
  def __sub__(self,other):

    if isinstance(other,int):
      other = Duration(other)
    if not isinstance(other,Duration):
      return NotImplemented
    
    new = self.copy()
    if self.rounds==Duration.INF:
      new.rounds = Duration.INF
    elif other.rounds==Duration.INF:
      new.rounds = 0
    else:
      new.rounds = self.rounds-other.rounds
    return new
  
  def __rsub__(self,other):

    if isinstance(other,int):
      other = Duration(other)
    if not isinstance(other,Duration):
      return NotImplemented
    
    new = self.copy()
    if other.rounds==Duration.INF:
      new.rounds = Duration.INF
    elif self.rounds==Duration.INF:
      new.rounds = 0
    else:
      new.rounds = other.rounds-self.rounds
    return new

  # decompose into sum of years, days, hours, minutes, rounds
  # @return (str)
  def __str__(self):

    if self.rounds==Duration.INF:
      return 'infinite'
    
    if self.rounds==0:
      return 'expired'

    s = []
    x = self.rounds
    for (num,name) in Duration.NAMES:
      if num<=x:
        s.append('%s%s' % (x//num,name))
        x = x%num
    return '+'.join(s)
  
  def __repr__(self):
    return '<Duration %s>' % str(self)
