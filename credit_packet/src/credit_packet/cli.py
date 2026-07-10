import argparse
from pathlib import Path
from .config import get_settings
from .sec_client import SECClient
from .packet import build_packet
from .render import render_markdown


def main():
    parser = argparse.ArgumentParser(prog='credit_packet')
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    b.add_argument('--ticker', required=True)
    b.add_argument('--years', type=int, default=3)
    b.add_argument('--output', default='outputs/packet.md')
    args = parser.parse_args()

    if args.command == 'build':
        out = Path(args.output)
        settings = get_settings()
        client = SECClient(settings)
        packet = build_packet(client, settings, args.ticker, args.years)

        suffix = out.suffix.lower()
        out.parent.mkdir(parents=True, exist_ok=True)
        if suffix == '.md':
            md = render_markdown(packet)
            out.write_text(md, encoding='utf-8')
        elif suffix == '.xlsx':
            from .excel_render import render_excel
            render_excel(packet, out)
        else:
            raise ValueError(f'Unsupported output extension: {suffix}. Use .md or .xlsx')
        print(f'Built packet for {packet.company.ticker} -> {out}')


if __name__ == '__main__':
    main()
