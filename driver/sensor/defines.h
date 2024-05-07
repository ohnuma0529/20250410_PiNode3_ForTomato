#ifndef __DEFINES_H__
/*********************************************************************
  defines.h
    各種定義ファイル

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#define __DEFINES_H__

#define ENABLE_I2C

#ifdef ENABLE_I2C
#define ENABLE_S1133
#define ENABLE_SHT25
#endif /* ENABLE_I2C */

#define ERROR_OK		 0
#define ERROR_INITIALIZED	-1
#define ERROR_FAIL_OPEN		-2
#define ERROR_FAIL_IOCTL	-3
#define ERROR_FAIL_READ		-4
#define ERROR_FAIL_WRITE	-5
#define ERROR_FAIL_CRC		-6
#define ERROR_UNKNOWN_ID	-11
#define ERROR_UNKNOWN_REGISTER	-12
#define ERROR_BUFFER_ADDRESS	-13

static const char VERSION_MAJOR[]="1";
static const char VERSION_MINOR[]="0";
static const char VERSION_PATCH[]="0";
static const char COPYRIGHT[]="Copyright (c) 2019 MinenoLab.\nCopyright (c) 2019 Akihisa ONODA";

#endif /* __DEFINES_H__ */

