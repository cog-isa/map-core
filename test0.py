import argparse
import os
import sys

from mapcore.planning.mapplanner import MapPlanner

from config_master import create_config, get_config
import platform
from memory_profiler import profile

@profile
def main(args):
    if platform.system() != 'Windows':
        delim = '/'
    else:
        delim = '\\'
    argparser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    argparser.add_argument(dest='problem', nargs='?')
    argparser.add_argument(dest='agpath', nargs='?')
    argparser.add_argument(dest='agtype', nargs='?')
    argparser.add_argument(dest='backward', nargs='?')
    argparser.add_argument(dest='config_path', nargs='?')
    args = argparser.parse_args(args)
    if args.problem and args.agpath and args.agtype:
        if not args.config_path:
            path = create_config(benchmark=os.path.abspath(args.problem), delim=delim,
                                 task_type='pddl', agpath = args.agpath, agtype = args.agtype, backward=args.backward)
        else:
            path = args.config_path
    else:
        if not args.config_path:
            path = create_config(task_num = '5', delim=delim, task_type = 'pddl')
        else:
            path = args.config_path

    # after 1 time creating config simply send a path
    planner = MapPlanner(**get_config(path))
    solution = planner.search()
    return solution


if __name__ == '__main__':
    main(sys.argv[1:])
