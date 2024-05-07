#ifndef __DRIVER_SHT25_H__
/*********************************************************************
  driver_sht25.h
    SHT25温湿度センサモジュールドライバソフトウェア

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#define __DRIVER_SHT25_H__
#include "defines.h"
#ifdef ENABLE_SHT25

#define SHT25_REG_TEMP          0xF3
#define SHT25_REG_HUMI          0xF5

int get_sht25(int, double *, unsigned char);

#define get_sht25_temp(id, buffer)      get_sht25(id, buffer, SHT25_REG_TEMP)
#define get_sht25_humi(id, buffer)      get_sht25(id, buffer, SHT25_REG_HUMI)
#endif /* ENABLE_SHT25 */

#endif /* __DRIVER_SHT25_H__ */

