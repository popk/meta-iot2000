#!/bin/sh      

DEVICE_TYPE=$(mount | head -n1 | cut -f 1 -d ' ' | cut -f 3 -d / | head -c 1) # returns 's' for boot from USB, 'm' for boot from SD

if [ $DEVICE_TYPE == "s" ]
	then
		ROOT_PARTITION="/dev/sda2"
		ROOT_DEVICE="/dev/sda"
		PART_NUMBER=2 
	elif [ $DEVICE_TYPE=="m" ]
		then
			ROOT_PARTITION="/dev/mmcblk0p2"
			ROOT_DEVICE="/dev/mmcblk0"
			PART_NUMBER=2 
	else
		echo "Cannot determine boot device."
		exit
fi

START_BLOCK=$(parted $ROOT_DEVICE -ms unit s p | grep "^2" | cut -f 2 -d: | rev | cut -c 2- | rev)


fdisk $ROOT_DEVICE <<EOF
p
d
$PART_NUMBER
n
p
$PART_NUMBER
$START_BLOCK


p
w
EOF

cat <<EOF > /etc/init.d/resize2fs_once
#!/bin/sh
### BEGIN INIT INFO
# Provides:          resize2fs_once
# Required-Start:
# Required-Stop:
# Default-Start: 3
# Default-Stop:
# Short-Description: Resize the root filesystem to fill partition
# Description:
### END INIT INFO
case "\$1" in
	start)
		resize2fs $ROOT_PARTITION &&
		update-rc.d -f resize2fs_once remove &&
		rm /etc/init.d/resize2fs_once		
		;;
esac 

EOF

chmod +x /etc/init.d/resize2fs_once &&
update-rc.d resize2fs_once defaults

