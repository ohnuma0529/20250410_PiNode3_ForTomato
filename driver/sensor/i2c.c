/*********************************************************************
  i2c.c
    I2Cドライバソフトウェア

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include "defines.h"
#ifdef ENABLE_I2C
#include "i2c.h"

static const int I2C_BUS_WAIT = 200000;

int
i2c_open(int address)
{
	int fd;

        if ((fd = open(I2C_1, O_RDWR)) < 0) {
                printf("Faild to open i2c port\n");
                return ERROR_FAIL_OPEN;
        }

        if (ioctl(fd, I2C_SLAVE, address) < 0) {
                printf("Unable to get bus access to talk to slave\n");
                return ERROR_FAIL_IOCTL;
        }

	return fd;
}

void
i2c_close(int fd)
{
	close(fd);
}

void
i2c_wait_bus(void)
{
	usleep(I2C_BUS_WAIT);
}
#endif /* ENABLE_I2C */
