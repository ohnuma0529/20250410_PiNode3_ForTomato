/*********************************************************************
  driver_sHT25.c
    SHT25温湿度センサモジュールドライバソフトウェア

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

#include "defines.h"
#ifdef ENABLE_SHT25
#include "i2c.h"
#include "driver_sht25.h"

#define SHT25_ADDR		0x40

#define SHT25_LEN_WRITE_REG	1
#define SHT25_LEN_READ_REG	2

int
get_sht25(int id, double *buffer, unsigned char reg)
{
        int fd;
        int res; 
	int address;
        unsigned char dat[4];
	int tmp;

	if (id != 0) {
		return ERROR_UNKNOWN_ID;
	}

	if (reg != SHT25_REG_TEMP &&
	    reg != SHT25_REG_HUMI) {
		return ERROR_UNKNOWN_REGISTER;
	}
	
	if (buffer == NULL) {
		return ERROR_BUFFER_ADDRESS;
	}

	address = SHT25_ADDR;
        if ((fd = i2c_open(address)) < 0) {
                return fd;
        }
	i2c_wait_bus();

        if ((write(fd, &reg, SHT25_LEN_WRITE_REG)) != SHT25_LEN_WRITE_REG) { 
                return ERROR_FAIL_WRITE;
        }
	i2c_wait_bus();

        if ((res = read(fd, dat, SHT25_LEN_READ_REG)) != SHT25_LEN_READ_REG) { 
                return ERROR_FAIL_READ;
        }

	tmp = ((int)(dat[0] & 0xFF) << 8) + (int)(dat[1] & 0xFF);
	if (reg == SHT25_REG_TEMP) {
		*buffer = -46.85 + ((((double)tmp) * 175.72) / 65536.0);
	} else {
		*buffer = -6.0   + ((((double)tmp) * 125.0)  / 65536.0);
	}

	i2c_close(fd);

	return ERROR_OK;
}
#endif /* ENABLE_SHT25 */
