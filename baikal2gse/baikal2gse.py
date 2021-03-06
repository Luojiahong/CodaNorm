#coding: utf-8
"""
Convert baikal file to seisan format
"""
__version__="0.0.1"
COMPANY_NAME = 'GIN'
APP_NAME = 'baikal2gse'

import os
import sys
import datetime
import numpy as np
import argparse

from baikal import BaikalFile

from obspy.core import UTCDateTime
from obspy.core import Stream
from obspy.core import Trace

from obspy.gse2 import writeGSE2


DEFAULT_STATS = {
    'network': "NT",
    'location': "LOC",
    "calib": 1.0,
    "gse2": {
        "lat": 0.,
        "lon": 0.,
        "elev": 0.,
        'coordsys': "WGS84",
        "edepth": 0.,
    },
}

CHANNELS = ("N", "E", "Z")


def write_seisan(filename, args):
    """ writes seisan file from baikal one """
    bf = BaikalFile(filename)
    if not bf.valid:
        print("Invalid file {}".format(filename))
        return
    header = bf.MainHeader
    # datetime
    date = datetime.datetime(header["year"], header["month"], header["day"])
    delta = datetime.timedelta(seconds=header["to"])
    dt = date + delta
    _time = dt.time() # time
    # make utc datetime
    utcdatetime = UTCDateTime(date.year, date.month, date.day,
        _time.hour, _time.minute, _time.second, _time.microsecond, precision=3)
    bf.traces = bf.traces.astype(np.int32)
    bf.traces = bf.traces[:3]
    traces = []
    for channel, data in zip(CHANNELS, bf.traces):
        stats = DEFAULT_STATS.copy()
        stats.update({
            "station": header['station'].upper()[:3],
            'channel': channel,
            'sampling_rate': int( 1./header["dt"] ),
            "delta": header["dt"],
            "npts": data.size,#shape[0]
            'starttime': utcdatetime,
        })
        # save coordinates
        stats['gse2']["lat"] = header['latitude']
        stats['gse2']["lon"] = header["longitude"]
        trace = Trace(data=data, header=stats)
        traces.append(trace)
    # create Stream
    stream = Stream(traces)
    #== write seisan
    # date
    name = "{year:04}-{month:02}-{day:02}".format(**header)
    # time
    name += "-{t.hour:02}-{t.minute:02}".format(t=stats['starttime'])
    # + station name + Day_of_Year
    name += "{0}__{1:03}".format(stats["station"], stats['starttime'].timetuple().tm_yday)
    print('Writing GSE2 file %s.' % name)
    writeGSE2(stream, os.path.join(args.outdir, name))


def main(args):
    """ convert files (or directories) to gse2 format """
    # parse arguments
    dirs = args.dirs
    outdir = args.outdir
    if not os.path.exists(outdir): os.makedirs(outdir)
    # create Stream
    stream = Stream()
    # can be multiple directories
    for path in args.dirs:
        if path == outdir:
            print("Cannot use same path for reading and writing! Skip...")
            continue
        if not os.path.exists(path):
            print("Path %s not found" % path)
            continue
        # may be it is file
        if os.path.isfile(path):
            write_seisan(path, args)
        else:
            # read xx files in each dir
            files = [os.path.join(path, s) for s in os.listdir(path)]
            for filename in files:
                # if not file, warn and skip
                if not os.path.isfile(filename):
                    print("%s is not file! Skipping...")
                else:
                    write_seisan(filename, args)


if __name__ == "__main__":
    #===========================================================================
    parser = argparse.ArgumentParser()
    parser.add_argument('-V', '--version', action='version', 
        version='%(prog)s.' + __version__)
    parser.add_argument("dirs", nargs='+', help="directories to convert")
    parser.add_argument("-o", "--outdir", dest="outdir", default="gse2",
        help="path for output data (default is \"gse2\")")
    args = parser.parse_args()
    #===========================================================================
    # convert files in arguments, into one file in Baikal-5 format
    try:
        main(args)
    except (ValueError,) as e:
        print("Error: {}".format(e))
        sys.exit(1)

