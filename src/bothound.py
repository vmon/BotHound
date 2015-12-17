import logging
import optparse
import re
import sys
import threading
import pdb

from bothound_live_sniffer import BothoundLiveSniffer

def main():
    parser = optparse.OptionParser()
    parser.add_option("-v", "--verbose", dest="verbose",
                      help="Be verbose in output, don't daemonise",
                      action="store_true")
    
    parser.add_option("-B", "--bindstrings",
                      action="store", dest="bindstrings",
                      default="tcp://127.0.0.1:22621",
                      help="URI(s) to bind to, if more than one should be comma separated")
                      
    parser.add_option("-P", "--passphrase",
                      action="store", dest="passphrase",
                      default="drawnandquarterly",
                      help="reads the key from command line")

    parser.add_option("-T", "--logtags",
                      action="store", dest="logtags",
                      default="botbanger_log",
                      help="distinguisher of the type of the receiving log, if more than one, it should be come comma separated")

    parser.add_option("-L", "--logfile",
                      action="store", dest="logfile",
                      default="logfetcher.log",
                      help="File to log to")

    parser.add_option("-c", "--conf",
                      action="store", dest="conffile",
                      default="/etc/botbanger/botbanger.conf",
                      help="Path to config file")

    (options, args) = parser.parse_args()

    if options.verbose:
        mainlogger = logging.getLogger()
        logging.basicConfig(level=logging.DEBUG)
        log_stream = logging.StreamHandler(sys.stdout)
        log_stream.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_stream.setFormatter(formatter)
        mainlogger.addHandler(log_stream)
    else:
        logger = logging.getLogger('logfetcher')
        hdlr = logging.FileHandler(options.logfile)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.setLevel(logging.DEBUG)

    lfetcher = BothoundLiveSniffer(options.bindstrings, options.passphrase, options.conffile, options.verbose)
    lfetcher.run()

if __name__ == "__main__":
    main()
