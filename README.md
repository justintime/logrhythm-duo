# logrhythm-duo - Import Duo MFA logs into LogRhythm

The code in this project is heavily based on the example provided by the [duo_client module](https://github.com/duosecurity/duo_client_python/tree/master/examples/splunk).

Some of the additions are:
 * Improved performance in cases where a large amount of logs were being fetched
 * Fixed some code that forced it to be ran on Windows.  The code now works on Windows, Mac, and Linux.
 * Added support for command-line arguments and help documentation.
 * Detects when Duo starts throttling requests, and exits cleanly.
 * The example only logged to STDOUT.  This version implements a TimedRotatingFile logger that will log the messages to individual log files, of which are rotated nightly and 
kept for 7 days.  This helps ensure that no logs are lost due to truncation, etc, while also ensuring it doesn't eventually fill up the disk.

This script is intended to be run from any operating system that can run Python.  Use cron on Linux, or a scheduled task on Windows.

## Performance
On my local Macbook Pro, it takes just over 3 seconds to download the limit (1,000 entries x 3 logs = 3,000 logs), including the startup time for Python.  Because it performs well, I think 
that enabling a system service mode for this script would likely be overkill.

## Configure Duo

Setup the Duo side of things by following the "First Steps" section at https://duo.com/docs/splunkapp.  Make note of these:
 * "Integration Key" (ikey)
 * "Secret Key" (skey)
 * "API Hostname" (host)

## Installation of LogRhythm-Duo

### Windows Only - Install Python and download zip file
Download the latest Python3 at https://www.python.org/downloads/windows/

Then, download the code from this project at https://github.com/justintime/logrhythm-duo/archive/master.zip  Extract the 
resulting file to a directory named ```C:\LogRhythm\LogRhythm-Duo```.  Once extracted, edit the duo.conf file in ```C:\LogRhythm\LogRhythm-Duo\```.

### Linux Only - create normal user, setup cron
Since we don't need elevated permissions to run this, let's create a dedicated user.

``` bash
# Create our user:
sudo useradd -d /home/logrhythm -s /bin/bash -m logrhythm
# Create our directory and make logrhythm the owner of it:
sudo mkdir /opt/logrhythm-duo && sudo chown logrhythm:logrhythm /opt/logrhythm-duo && sudo chmod 700 /opt/logrhythm-duo
# Become the new user and clone this repo:
sudo su - logrhythm -c 'git clone https://github.com/justintime/logrhythm-duo.git /opt/logrhythm-duo'
# Edit duo.conf and put in your API keys and host:
sudo nano /opt/logrhythm-duo/duo.conf
```
### Configure duo.conf
Configure duo.conf by setting the ikey, skey, and host values, as shown to you in your Duo control panel under the Admin app.

### Install dependencies
To install the dependencies of this script, run the following command from the directory of the script:
``` bash
pip3 install --requirement requirements.txt
```

### Linux - Configure cron
``` bash
# Create the cronjob:
sudo cp /opt/logrhythm-duo/resources/logrhythm-duo /etc/cron.d
```

### Windows - Configure Task Scheduler

## Setup of MPE Parsing Rules

## Setup of Duo Log Source

 1. Deployment Manager -> System Monitors tab, double click the machine running the logrhythm-duo script.
 1. Right click the grid, and select "New".
 1. For the "Log Source Type", select your new "Flat File - Duo Security 2FA" source.
 1. Select "LogRhythm Default" from the Log MPE Policy.
 1. Select the "Flat File Settings" tab.
 1. Put the full path to the log files in the File Path box.  If you used the examples for Linux, you'd 
 use '/opt/logrhythm-duo/logs/*.log*'
 1. In the "Date Parsing Format" field, select 'Linux Audit Log (Unix time)'
 1. Click the "OK" button.


### Testing
Run the script verbosely from the command line:
``` bash
python logrhythm-duo.py -v
```
You should get some messages about how many logs the script downloaded.  If you did, you're good to go and can configure the script to run from Task Scheduler or Cron

