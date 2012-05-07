"""Git based time tracking"""

import json
import optparse
import os
import sys

from datetime import (datetime, timedelta)

import git

__version__ = "0.2.2"

usage = """git time [options]
   or: git time start [options]
   or: git time stop [options]
   or: git time show [options]
"""

parser = optparse.OptionParser(usage)

parser.add_option('-b', '--branch', action='store', dest='branch',
                  default='hammertime',
                  help='Sets the name of the branch that saves timing data.')

parser.add_option('-d', '--dir', action='store', dest='folder',
                  default='.hammertime',
                  help='Sets the folder that data is saved in.')

parser.add_option('-f', '--file', action='store', dest='file',
                  default='times.json',
                  help='Sets the file that data is saved in.')

parser.add_option('-i', '--indent', action='store', dest='indent',
                  default=None,
                  help='Add indentation to JSON output, eg: -i 4')

parser.add_option('-m', '--message', action='store', dest='message',
                  default=False,
                  help='Optional message with the start/stop commands')

opts, args = parser.parse_args()

try:
    opts.indent = int(opts.indent)
except TypeError:
    opts.indent = None

DIR = os.getcwd()
FOLDER = lambda repo: os.path.join(repo.working_dir, opts.folder)
FILE = lambda repo: os.path.join(repo.working_dir, opts.folder, opts.file)

try:
    cmd = args[0]
except IndexError:
    cmd = 'default'


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

    def start(self, opts):
        """Start a new timer, if none active."""
        self['times'].append({
            'start': {
                'time': datetime.utcnow(),
                'message': opts.message or None
            }
        })

    def stop(self, opts):
        """Stop running timer."""
        time = self['times'][-1]

        now = datetime.utcnow()

        time.update({
            'stop': {
                'time': now,
                'message': opts.message or None
            }
        })

        if time['start']['time']:
            time['delta'] = now - time['start']['time']
        else:
            time['delta'] = None



def init(repo, opts):
    """Initiate and load timer data."""
    # Make sure a branch is available
    if not hasattr(repo.heads, opts.branch):
        repo.git.branch(opts.branch)

    # Switch the branch
    getattr(repo.heads, opts.branch).checkout()

    # Make sure there's a folder
    if not os.path.exists(FOLDER(repo)):
        os.mkdir(FOLDER(repo))

    # And the data file
    if not os.path.exists(FILE(repo)):
        open(FILE(repo), 'w').close()

    # Load the data
    try:
        data = json.load(open(FILE(repo)), object_hook=datetime_hook)
    except ValueError:
        data = dict(times=[])

    timer = Timer()
    timer.update(data)
    return timer


def write(repo, opts, timer):
    """Write timer data."""
    json.dump(timer, open(FILE(repo), 'w'), cls=DatetimeEncoder)
    repo.index.add([FILE(repo)])
    repo.index.commit(opts.message or 'Hammertime!')


def start(repo, opts, timer):
    """Start timer."""
    timer.start(opts)


def stop(repo, opts, timer):
    """Stop timer."""
    timer.stop(opts)


def total(repo, opts, timer):
    """Report total running time."""
    total = timedelta(seconds=0)

    for time in timer['times']:
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


def show(repo, opts, timer):
    """Show timer data."""
    print json.dumps(timer, indent=opts.indent, cls=DatetimeEncoder)


def default(repo, opts, timer):
    """Default command to display usage."""
    parser.print_usage()


commands = dict(start=start, stop=stop, show=show, default=default,
                total=total)


def main():
    """Main command line interface."""
    try:
        repo = git.Repo(DIR)
    except git.exc.InvalidGitRepositoryError:
        print "fatal: Not a git repository"
        sys.exit(1)

    if cmd not in commands.keys():
        parser.print_usage()
        sys.exit(1)

    if len(repo.heads) == 0:
        print """fatal: No initial commit.
       Perhaps create a master branch and an inital commit."""
        sys.exit(1)

    try:
        # Save old branch
        branch = repo.head.reference

        # Stash current changes to not lose anything
        repo.git.stash()

        timer = init(repo, opts)

        commands[cmd](repo, opts, timer)

        if cmd in ['start', 'stop']:
            write(repo, opts, timer)
    finally:
        # Switch back to old branch
        getattr(repo.heads, branch.name).checkout()

        # Pop the stashed changes
        try:
            repo.git.stash('pop')
        except:
            pass

if __name__ == '__main__':
    main()
