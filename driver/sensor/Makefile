CP = \/bin/cp -f
CC = /usr/bin/gcc
RM = \/bin/rm -f

OBJS  = i2c.o
OBJS += driver_s1133.o driver_sht25.o
OBJS += main.o

TARGET = read_sensor

CFLAGS = -Wall

.SUFFIXES: .c .o

all : $(TARGET)

$(TARGET) : $(OBJS)
	$(CC) $(OBJS) -o $(TARGET) $(CFLAGS)

.c.o : $<
	$(CC) -c $(CFLAGS) $<

install :
	$(CP) ./$(TARGET) /usr/local/bin/

uninstall :
	$(RM) /usr/local/bin/$(TARGET)

clean :
	$(RM) $(OBJS) $(TARGET)

