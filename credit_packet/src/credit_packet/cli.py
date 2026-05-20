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
        settings=get_settings()
        client=SECClient(settings)
        packet=build_packet(client, settings, ticker=args.ticker, years=args.years)
        md=render_markdown(packet)
        out=Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md)
        print(f"Built packet for {packet.company.ticker} ({packet.company.name}) -> {out}")
        print(f"Filings: {len(packet.filings)} | Periods: {len(packet.financial_periods)} | Flags: {len(packet.watchlist_flags)}")

if __name__ == '__main__':
    main()
