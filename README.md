# logrhythm-duo - Import Duo MFA logs into LogRhythm

The code in this project is heavily based on the example provided by the [duo_client module](https://github.com/duosecurity/duo_client_python/tree/master/examples/splunk).

Some of the additions are:
 * Improved performance in cases where a large amount of logs were being fetched
 * Fixed some code that forced it to be ran on Windows.  The code now works on Windows, Mac, and Linux.
 * Added support for command-line arguments and help documentation.
 * Detects when Duo starts throttling requests, and exits cleanly.
 * The example only logged to STDOUT.  This version implements a TimedRotatingFile logger that will log the messages to individual log files, of which are rotated nightly and 
kept for 7 days.  This helps ensure that no logs are lost due to truncation, etc, while also ensuring it doesn't eventually fill up the disk.

This script is intended to be run from any operating system that can run Python.  Use cron on Linux #TODO document this, or a scheduled task on Windows #TODO powershell?.

## Performance
On my local Macbook Pro, it takes just over 3 seconds to download the limit (1,000 entries x 3 logs = 3,000 logs), including the startup time for Python.  Because it performs well, I think 
that enabling a system service mode for this script would likely be overkill.

## Configure Duo

Setup the Duo side of things by following the "First Steps" section at https://duo.com/docs/splunkapp

## Configure this script
### Configure duo.conf
Configure duo.conf by setting the ikey, skey, and host values, as shown to you in your Duo control panel under the Admin app.

### Install Python


### Install dependencies
To install the dependencies of this script, run the following command from the directory of the script:
``` bash
pip install --requirement requirements.txt
```

### Test run
Run the script interactively:
``` bash
python logrhythm-duo.py -v
```
You should get some messages about how many logs the script downloaded.  If you did, you're good to go and can configure the script to run from Task Scheduler or Cron

