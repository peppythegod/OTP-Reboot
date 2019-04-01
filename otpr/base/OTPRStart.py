import __builtin__

__builtin__.__live__ = False

import OTPRBase

base = OTPRBase.OTPRBase()
base.run()