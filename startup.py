from uvloop import install as uvloopInstaller
from RF.bot import bot

VERSION = "0.8.5"

def main():
    uvloopInstaller()
    bot.run(VERSION)

if __name__ == '__main__':
    main()