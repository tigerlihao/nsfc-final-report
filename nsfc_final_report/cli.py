import argparse
from .client import NSFCClient

def main():
    parser = argparse.ArgumentParser(prog='nsfc-final-report')
    sub = parser.add_subparsers(dest='cmd')

    p_search = sub.add_parser('search')
    p_search.add_argument('--keyword', '-k', default='')
    p_search.add_argument('--page', type=int, default=0)
    p_search.add_argument('--size', type=int, default=10)

    p_info = sub.add_parser('info')
    p_info.add_argument('project_id')

    p_dl = sub.add_parser('download')
    p_dl.add_argument('project_id')
    p_dl.add_argument('--out', '-o', default=None)
    p_dl.add_argument('--max-pages', type=int, default=50)
    p_dl.add_argument('--force', action='store_true', help='redownload existing files')

    p_batch = sub.add_parser('batch')
    p_batch.add_argument('--keyword', '-k', default='')
    p_batch.add_argument('--out', '-o', default=None)
    p_batch.add_argument('--page-size', type=int, default=10)
    p_batch.add_argument('--force', action='store_true', help='redownload reports')
    p_batch.add_argument('--jsonl', default=None, help='path to write search results jsonl')

    args = parser.parse_args()
    client = NSFCClient()
    if args.cmd == 'search':
        res = client.search(fuzzyKeyword=args.keyword, pageNum=args.page, pageSize=args.size)
        print(res)
    elif args.cmd == 'info':
        print(client.get_project_info(args.project_id))
    elif args.cmd == 'download':
        files = client.download_report(args.project_id, out_dir=args.out, max_pages=args.max_pages, force=args.force)
        print('\n'.join(files))
    elif args.cmd == 'batch':
        processed = client.batch_fetch(fuzzyKeyword=args.keyword, out_dir=args.out, pageSize=args.page_size, force=args.force, jsonl_path=args.jsonl)
        print('\n'.join(processed))
    else:
        parser.print_help()
