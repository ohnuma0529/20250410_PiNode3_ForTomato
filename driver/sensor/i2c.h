#ifndef __I2C_H__
/*********************************************************************
  i2c.h
    I2Cドライバソフトウェア

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#define __I2C_H__

#include "defines.h"
#ifdef ENABLE_I2C
#include <linux/i2c-dev.h>

#define I2C_1	"/dev/i2c-1"

int  i2c_open(int);
void i2c_close(int);
void i2c_wait_bus(void);
#endif /* ENABLE_I2C */
#endif /* __I2C_H__ */

