/*********************************************************************
  driver_s1133.c
    S1133照度センサモジュールドライバソフトウェア

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

#include "defines.h"
#ifdef ENABLE_S1133
#include "i2c.h"
#include "driver_s1133.h"

#define S1133_ADDR_0		0x30
#define S1133_ADDR_1		0x31

#define S1133_LEN_READ_REG	3
#define S1133_POS_READ_CRC	2

const unsigned short CRC_POLYNOMIAL = 0x131;  //P(x)=x^8+x^5+x^4+1 = 100110001

static unsigned char
calc_crc8(unsigned char *data, int terminate)
{
	int i, j;
	unsigned short crc = 0;

	for (i = 0; i < terminate; i++) {
		crc ^= (unsigned short)(data[i] & 0x0FF);
		for (j = 0; j < 8; j++) {
			if (crc & 0x80) {
				crc <<= 1;
				crc ^= CRC_POLYNOMIAL;
			} else {
				crc <<= 1;
			}
		}
	}

	return (unsigned char)(crc & 0x0FF);
}


int
get_s1133(int id, double *buffer)
{
        int fd;
        int res; 
	int address;
        unsigned char dat[4];
	int tmp;

	int idx;
	unsigned char crc;
	const double range[] = {0.0, 1.0, 4.0, 16.0};

	if (id < 0 || id > 1) {
		return ERROR_UNKNOWN_ID;
	}

	if (buffer == NULL) {
		return ERROR_BUFFER_ADDRESS;
	}
	
	address = (id == 0) ? S1133_ADDR_0 : S1133_ADDR_1;
        if ((fd = i2c_open(address)) < 0) {
                return fd;
        }

        if ((res = read(fd, dat, S1133_LEN_READ_REG)) != S1133_LEN_READ_REG) { 
                return ERROR_FAIL_READ;
        }
        i2c_wait_bus();

	crc = calc_crc8(dat, S1133_POS_READ_CRC);
	if (crc != dat[S1133_POS_READ_CRC]) {
		return ERROR_FAIL_CRC;
	}

	tmp = ((int)(dat[0] & 0xFF) << 4) + ((int)(dat[1] & 0xFF) >> 4);
	idx = ((int)dat[1] & 0x0c) >> 2;
	*buffer = ((double)tmp) / 4096.0 * 250000.0 / range[idx];

	i2c_close(fd);

	return ERROR_OK;
}
#endif /* ENABLE_S1133 */
