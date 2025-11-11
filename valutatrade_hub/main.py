import argparse
import shlex

from valutatrade_hub.cli.interface import COMMAND_HANDLERS


def build_parser():
    parser = argparse.ArgumentParser(prog='valutatrade')
    subparsers = parser.add_subparsers(dest='command')

    register_parser = subparsers.add_parser('register')
    register_parser.add_argument('--username', required=True)
    register_parser.add_argument('--password', required=True)

    login_parser = subparsers.add_parser('login')
    login_parser.add_argument('--username', required=True)
    login_parser.add_argument('--password', required=True)

    show_parser = subparsers.add_parser('show-portfolio')
    show_parser.add_argument('--base')

    buy_parser = subparsers.add_parser('buy')
    buy_parser.add_argument('--currency', required=True)
    buy_parser.add_argument('--amount', required=True, type=float)

    sell_parser = subparsers.add_parser('sell')
    sell_parser.add_argument('--currency', required=True)
    sell_parser.add_argument('--amount', required=True, type=float)

    rate_parser = subparsers.add_parser('get-rate')
    rate_parser.add_argument('--from', dest='from_currency', required=True)
    rate_parser.add_argument('--to', dest='to_currency', required=True)

    return parser


def execute_command(parser, args):
    if not getattr(args, 'command', None):
        parser.print_help()
        return

    handler = COMMAND_HANDLERS.get(args.command)
    if not handler:
        parser.print_help()
        return

    try:
        handler(args)
    except ValueError as error:
        print(error)


def main(argv=None):
    parser = build_parser()
    if argv:
        try:
            args = parser.parse_args(argv)
        except SystemExit:
            return
        execute_command(parser, args)
        return

    print("Введите команду (help для списка, exit для выхода)")
    while True:
        try:
            raw = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nВыход.')
            break

        if not raw:
            continue
        lower = raw.lower()
        if lower in ('exit', 'quit'):
            print('До встречи!')
            break
        if lower in ('help', '?'):
            parser.print_help()
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as error:
            print(f'Ошибка ввода: {error}')
            continue

        try:
            args = parser.parse_args(parts)
        except SystemExit:
            continue

        execute_command(parser, args)


if __name__ == '__main__':
    main()
