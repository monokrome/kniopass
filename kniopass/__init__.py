import argparse
import getpass
import logging
import os

from .kniopass import KnioPass
from .cli import KnioPassCLI


LOG = logging.getLogger()


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file')
    parser.add_argument('--create')
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--import-keepass')
    args = parser.parse_args()

    if args.import_keepass:
        from .keepass_cvs_import import read_keepass
        if os.path.isfile(args.create):
            raise Exception('File already exists. Refusing to overwrite')
        password = getpass.getpass('Password for {}: '.format(args.create))
        pw = KnioPass(filename=args.create, password=password)
        pw.rekey()
        pw.data = {}
        read_keepass(args.import_keepass, pw)
        pw.save()
        LOG.info('Imported %s to %s', args.import_keepass, args.create)
        return

    if args.generate:
        pw = KnioPassCLI.password_picker()
        print(pw)
        return

    if args.create:
        if os.path.isfile(args.create):
            raise Exception('File already exists. Refusing to overwrite')
        password = getpass.getpass('Password for {}: '.format(args.create))
        pw = KnioPass(filename=args.create, password=password)
        pw.rekey()
        pw.data = {}
        pw.save()
        LOG.info('Created new empty password store %s', args.create)
        return

    if args.file:
        if not os.path.isfile(args.file):
            raise Exception('File does not exist')
        password = getpass.getpass('Password for {}: '.format(args.file))
        pw = KnioPassCLI(filename=args.file, password=password)
        pw.load()
        pw.repl()


if __name__ == '__main__':
    main()
