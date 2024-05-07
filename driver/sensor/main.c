/*********************************************************************
  main.c
    メイン処理

  Copyright (c) 2019 Akihisa ONODA All rights reserved.
*********************************************************************/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <ctype.h>
#include <getopt.h>
#include "defines.h"
#include "driver_s1133.h"
#include "driver_sht25.h"

#define READ_SENSOR_PARAM_TYPE		't'
#define READ_SENSOR_PARAM_ID		'i'
#define READ_SENSOR_PARAM_MODE		'm'
#define READ_SENSOR_PARAM_VERSION	'v'
#define READ_SENSOR_PARAM_HELP		'h'

#ifdef ENABLE_S1133
#define READ_SENSOR_TYPE_S1133		"s1133"
#endif /* ENABLE_S1133 */
#ifdef ENABLE_SHT25
#define READ_SENSOR_TYPE_SHT25		"sht25"
#endif /* ENABLE_SHT25 */

#ifdef ENABLE_S1133
#define READ_SENSOR_MODE_LUX		"lux"
#endif /* ENABLE_S1133 */
#ifdef ENABLE_SHT25
#define READ_SENSOR_MODE_TEMP		"temp"
#define READ_SENSOR_MODE_HUMI		"humi"
#endif /* ENABLE_SHT25 */

#define BUFFER_SIZE			64

static struct option longopts[] = {
        { "type",               required_argument,      NULL,   READ_SENSOR_PARAM_TYPE },
        { "id",                 required_argument,      NULL,   READ_SENSOR_PARAM_ID },
        { "mode",               required_argument,      NULL,   READ_SENSOR_PARAM_MODE },
        { "version",            no_argument,            NULL,   READ_SENSOR_PARAM_VERSION },
        { "help",               no_argument,            NULL,   READ_SENSOR_PARAM_HELP },
        {0,                     0,                      0,      0}
};

enum {
#ifdef ENABLE_S1133
	SENSOR_TYPE_S1133 = 0,
#endif /* ENABLE_S1133 */
#ifdef ENABLE_SHT25
#ifndef ENABLE_S1133
	SENSOR_TYPE_SHT25 = 0,
#else /* ENABLE_S1133 */
	SENSOR_TYPE_SHT25,
#endif /* ENABLE_S1133 */
#endif /* ENABLE_SHT25 */
	SENSOR_TYPE_ZZZ
};

enum {
#ifdef ENABLE_S1133
	SENSOR_MODE_LUX = 0,
#endif /* ENABLE_S1133 */
#ifdef ENABLE_SHT25
#ifndef ENABLE_S1133
	SENSOR_MODE_TEMP = 0,
#else /* ENABLE_S1133 */
	SENSOR_MODE_TEMP,
#endif /* ENABLE_S1133 */
	SENSOR_MODE_HUMI,
#endif /* ENABLE_SHT25 */
	SENSOR_MODE_ZZZ
};


static int
str2int(char *string)
{
	int i, result = ERROR_INITIALIZED;
	
	if (string == NULL) {
		goto RESULT;
	}

	for (i = 0; i < strlen(string); i++) {
		if (!isdigit(string[i])) {
			goto RESULT;
		}
	}
	result = atoi(string);
	
RESULT:
	return result;
}


static void
print_version(void)
{
	printf("%s version %s.%s.%s\n%s\n", 
	       "read_sensor",
	       VERSION_MAJOR,
	       VERSION_MINOR,
	       VERSION_PATCH,
	       COPYRIGHT);
	exit(0);
}


static void
print_usage(void)
{
	char param[BUFFER_SIZE], type[BUFFER_SIZE], id[BUFFER_SIZE], mode[BUFFER_SIZE];
	snprintf(param, BUFFER_SIZE, "%s",
#if defined ENABLE_S1133 || defined ENABLE_SHT25
		 " [-t type] [-i id] [-m mode]"
#else /* ENABLE_S1133 || ENABLE_SHT25 */
		 ""
#endif /* ENABLE_S1133 || ENABLE_SHT25 */
		 );
	snprintf(type, BUFFER_SIZE, "%s%s%s",
#ifdef ENABLE_S1133
		 READ_SENSOR_TYPE_S1133
#else /* ENABLE_S1133 */
		 ""
#endif /* ENABLE_S1133 */
		 ,
#if defined ENABLE_S1133 && defined ENABLE_SHT25
		 " / "
#else /* ENABLE_S1133 || ENABLE_SHT25 */
		 ""
#endif /* ENABLE_S1133 || ENABLE_SHT25 */
		 ,
#ifdef ENABLE_SHT25
		 READ_SENSOR_TYPE_SHT25
#else /* ENABLE_SHT25 */
		 ""
#endif /* ENABLE_SHT25 */
		 );
	snprintf(id, BUFFER_SIZE, "%s",
#ifdef ENABLE_S1133
		 "0-1"
#elif defined ENABLE_SHT25
		 "0"
#else /* ENABLE_S1133 || ENABLE_SHT25 */
		 ""
#endif  /* ENABLE_S1133 || ENABLE_SHT25 */
		 );
	snprintf(mode, BUFFER_SIZE, "%s%s%s",
#ifdef ENABLE_S1133
		 READ_SENSOR_MODE_LUX
#else /* ENABLE_S1133 */
		 ""
#endif /* ENABLE_S1133 */
		 ,
#if defined ENABLE_S1133 && defined ENABLE_SHT25
		 " / "
#else /* ENABLE_S1133 || ENABLE_SHT25 */
		 ""
#endif /* ENABLE_S1133 || ENABLE_SHT25 */
		 ,
#ifdef ENABLE_SHT25
		 READ_SENSOR_MODE_TEMP" / "READ_SENSOR_MODE_HUMI
#else /* ENABLE_SHT25 */
		 ""
#endif /* ENABLE_SHT25 */
		 );
	printf("Usage: %s [-hv]%s\n"
	       "                   type = %s,\n"
	       "                   id = %s,\n" 
	       "                   mode = %s\n", 
	       "read_sensor",
	       param, type, id, mode);
	exit(0);
}


int
main(int argc, char **argv) 
{
	int opt;
	int type = SENSOR_TYPE_ZZZ;
        int id = ERROR_INITIALIZED;
	int mode = SENSOR_MODE_ZZZ;
	int result = ERROR_INITIALIZED;
	double buffer = 0.0;

	while ((opt = getopt_long(argc, argv, "t:i:m:vh", longopts, NULL)) != -1) {
		switch (opt) {
		case READ_SENSOR_PARAM_TYPE:
#ifdef ENABLE_S1133
			if (strcasecmp(READ_SENSOR_TYPE_S1133, optarg) == 0 &&
			    strlen(READ_SENSOR_TYPE_S1133) == strlen(optarg)) {
				type = SENSOR_TYPE_S1133;
				mode = SENSOR_MODE_LUX;
			}
#endif /* ENABLE_S1133 */
#if defined ENABLE_S1133 && defined ENABLE_SHT25
			else
#endif /* ENABLE_S1133 && ENABLE_SHT25 */
#ifdef ENABLE_SHT25
			if (strcasecmp(READ_SENSOR_TYPE_SHT25, optarg) == 0 &&
			    strlen(READ_SENSOR_TYPE_SHT25) == strlen(optarg)) {
				type = SENSOR_TYPE_SHT25;
			}
#endif /* ENABLE_SHT25 */
#if defined ENABLE_S1133 || defined ENABLE_SHT25
			else
#endif /* ENABLE_S1133 || ENABLE_SHT25 */
			{
				type = SENSOR_TYPE_ZZZ;
			}
			break;
		case READ_SENSOR_PARAM_ID:
			id = str2int(optarg);
			break;
		case READ_SENSOR_PARAM_MODE:
#ifdef ENABLE_S1133
			if (strcasecmp(READ_SENSOR_MODE_LUX, optarg) == 0 &&
			    strlen(READ_SENSOR_MODE_LUX) == strlen(optarg)) {
				mode = SENSOR_MODE_LUX;
			}
#endif /* ENABLE_S1133 */
#if defined ENABLE_S1133 && defined ENABLE_SHT25
			else
#endif /* ENABLE_S1133 && ENABLE_SHT25 */
#ifdef ENABLE_SHT25
			if (strcasecmp(READ_SENSOR_MODE_TEMP, optarg) == 0 &&
				   strlen(READ_SENSOR_MODE_TEMP) == strlen(optarg)) {
				mode = SENSOR_MODE_TEMP;
			} else if (strcasecmp(READ_SENSOR_MODE_HUMI, optarg) == 0 &&
				   strlen(READ_SENSOR_MODE_HUMI) == strlen(optarg)) {
				mode = SENSOR_MODE_HUMI;
			}
#endif /* ENABLE_SHT25 */
#if defined ENABLE_S1133 || defined ENABLE_SHT25
			else
#endif /* ENABLE_S1133 || ENABLE_SHT25 */
			{
				mode = SENSOR_MODE_ZZZ;
			}
			break;
		case READ_SENSOR_PARAM_VERSION:
			print_version();
			break;
		case READ_SENSOR_PARAM_HELP:
			print_usage();
			break;
		default:
			break;
		}
	}

	switch (type) {
#ifdef ENABLE_S1133
	case SENSOR_TYPE_S1133:
		if (mode == SENSOR_MODE_LUX) {
			result = get_s1133(id, &buffer);
		} else {
			;
		}
		break;
#endif /* ENABLE_S1133 */
#ifdef ENABLE_SHT25
	case SENSOR_TYPE_SHT25:
		if (mode == SENSOR_MODE_TEMP) {
			result = get_sht25_temp(id, &buffer);
		} else if (mode == SENSOR_MODE_HUMI) {
			result = get_sht25_humi(id, &buffer);
		} else {
			;
		}
		break;
#endif /* ENABLE_SHT25 */
	default:
		break;
	}

	if (result == ERROR_OK) {
		printf("%8.3f\n", buffer);
	}

        return result;
}
