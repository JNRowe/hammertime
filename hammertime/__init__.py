"""Git based time tracking"""

__author__ = "Alen Mujezinovic <alen@caffeinehit.com>"
__copyright__ = "Copyright (c) 2011 Alen Mujezinovic <alen@caffeinehit.com>"
__license__ = "MIT"
__version__ = "0.2.2"

import json
import os
import sys

from datetime import (datetime, timedelta)

import argh
import git


def create_cmdline(commands):
    p = argh.ArghParser('\n'.join(__doc__.strip().splitlines()[2:]))

    p.add_argument('-b', '--branch', default='hammertime',
                   help='set the name of the branch that saves timing data')

    p.add_argument('-d', '--dir', dest='folder',  default='.hammertime',
                   help='sets the folder that data is saved in')

    p.add_argument('-f', '--file', default='times.json',
                   help='sets the file that data is saved in')

    p.add_commands(commands)

    return p


class DatetimeEncoder(json.JSONEncoder):

    """JSON encoding support for datetime and timedelta."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            # No need for milliseconds
            return str(obj).split('.')[0]

        return super(DatetimeEncoder, self).default(obj)


def datetime_hook(obj):
    """Decode datetime objects from JSON."""
    try:
        if obj.get('time', False):
            obj['time'] = datetime.strptime(obj.get('time'),
                                            '%Y-%m-%dT%H:%M:%S.%f')
    finally:
        return obj


class Timer(dict):

    """Base timer container."""

    def start(self, message):
        """Start a new timer, if none active."""
        self['times'].append({
            'start': {
                'time': datetime.utcnow(),
                'message': message or None
            }
        })

    def stop(self, message):
        """Stop running timer."""
        time = self['times'][-1]

        now = datetime.utcnow()

        time.update({
            'stop': {
                'time': now,
                'message': message or None
            }
        })

        time['delta'] = now - time['start']['time']


def init(repo, args, switch_branch=True):
    """Initiate and load timer data."""
    if switch_branch:
        # Make sure a branch is available
        if not args.branch in repo.heads:
            repo.git.branch(args.branch)

        # Switch the branch
        getattr(repo.heads, args.branch).checkout()

    folder = os.path.join(repo.working_dir, args.folder)
    file = os.path.join(repo.working_dir, args.folder, args.file)

    # Make sure there's a folder
    if not os.path.exists(folder):
        os.mkdir(folder)

    # And the data file
    if not os.path.exists(file):
        open(file, 'w').close()

    # Load the data
    try:
        data = json.load(open(file), object_hook=datetime_hook)
    except ValueError:
        data = dict(times=[])

    timer = Timer()
    timer.update(data)
    return timer


def write(repo, args, timer):
    """Write timer data."""
    file = os.path.join(repo.working_dir, args.folder, args.file)
    json.dump(timer, open(file, 'w'), cls=DatetimeEncoder)
    repo.index.add([file, ])
    repo.index.commit(args.message or 'Hammertime!')


@argh.arg('-m', '--message', help='optional start message')
def start(args):
    """Start timer."""
    if len(args.timer['times']) > 0 and 'start' in args.timer['times'][-1]:
        raise argh.CommandError('Already running!')
    args.timer.start(args.message)


@argh.arg('-m', '--message', help='optional stop message')
def stop(args):
    """Stop timer."""
    if len(args.timer['times']) == 0:
        raise argh.CommandError('No entries to stop!')
    args.timer.stop(args.message)


def total(args):
    """Report total running time."""
    total = timedelta(seconds=0)

    for time in args.timer['times']:
        try:
            bits = map(int, time['delta'].split(':'))
            delta = (
                timedelta(seconds=bits[0] * 3600)
                + timedelta(seconds=bits[1] * 60)
                + timedelta(seconds=bits[2])
            )
        except (KeyError, IndexError):
            delta = timedelta(seconds=0)

        total += delta

    print total


@argh.arg('-i', '--indent', type=int,
          help='add indentation to JSON output, eg: -i 4')
def show(args):
    """Show timer data."""
    print json.dumps(args.timer, indent=args.indent, cls=DatetimeEncoder)


def main():
    """Main command line interface."""

    parser = create_cmdline([start, stop, show, total])
    args = parser.parse_args()

    try:
        repo = git.Repo(os.getcwd())
    except git.exc.InvalidGitRepositoryError:
        print "fatal: Not a git repository"
        sys.exit(1)

    if len(repo.heads) == 0:
        print """fatal: No initial commit.
       Perhaps create a master branch and an initial commit."""
        sys.exit(1)

    try:
        # Save old branch
        orig_branch = repo.active_branch
        switch_branch = not orig_branch.name == args.branch

        if switch_branch:
            # Stash current changes to not lose anything
            repo.git.stash()

        timer = init(repo, args, switch_branch=switch_branch)

        def attach_timer(args):
            args.timer = timer
        parser.dispatch(pre_call=attach_timer)

        if args.function.__name__ in ['start', 'stop']:
            write(repo, args, timer)
    finally:
        if switch_branch:
            # Switch back to old branch
            getattr(repo.heads, orig_branch.name).checkout()

            # Pop the stashed changes
            try:
                repo.git.stash('pop')
            except:
                pass

if __name__ == '__main__':
    main()
