DIR=`dirname $0`
. $DIR/base-toggle.sh

isBlue
if [ $? == 1 ]; then
  boltLbCmd "$BLUE" RM
else
  boltLbCmd "$GREEN" RM
fi


if [ $ECHO_SETTINGS == "TRUE" ]; then
  boltLbCmd
fi
