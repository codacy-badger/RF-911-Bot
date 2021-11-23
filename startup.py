from uvloop import install
from RF.bot import *

VERSION = "0.8.0"

def main():
    install()
    bot.run(VERSION)

if __name__ == '__main__':
    main()