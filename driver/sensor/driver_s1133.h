#ifndef __DRIVER_S1133_H__
/*********************************************************************
  driver_s1133.h
    S1133照度センサモジュールドライバソフトウェア

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#define __DRIVER_S1133_H__
#include "defines.h"
#ifdef ENABLE_S1133
int get_s1133(int, double *);
#endif /* ENABLE_S1133 */

#endif /* __DRIVER_S1133_H__ */

