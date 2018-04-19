import numpy as np

def cast_type(ins, outs):
  #outs = ins
  Red = ins['Red']
  Green = ins['Green']
  Blue = ins['Blue']

  outs['Red'] = (255*Red.astype(int)/65535).astype(np.uint16)
  outs['Green'] = (255*Green.astype(int)/65535).astype(np.uint16)
  outs['Blue'] = (255*Blue.astype(int)/65535).astype(np.uint16)

  return True
