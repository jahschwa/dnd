class CharSheetError(Exception):
  pass

#####

class FieldError(CharSheetError):
  pass

class ProtectedError(FieldError):
  pass

class FormulaError(FieldError):
  pass

#####

class CharError(CharSheetError):
  pass

class DuplicateError(CharError):
  pass

class DependencyError(CharError):
  pass

class UserSkipException(CharError):
  pass

class UserQuitException(CharError):
  pass
