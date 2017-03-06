"""
Created on 18 April 2015

@author: vsochat

Test query times for deployed database
"""
import os
import time
import django
import numpy as np
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "afqvault.settings")
django.setup()
from afqvault.apps.afqmaps.models import Comparison
from afqvault.apps.afqmaps.models import Image
from afqvault.apps.afqmaps.models import Similarity
from afqvault.apps.afqmaps.utils import count_existing_comparisons, \
    count_processing_comparisons, get_existing_comparisons, count_possible_comparisons


time_log = dict()

# Count existing comparisons
times = []
for iter in range(0, 1000):
    start = time.time()
    number_comparisons = count_existing_comparisons(pk1=8)
    end = time.time()
    times.append(end - start)
time_log["count_existing_comparisons_single"] = np.mean(times)
print "count_existing_comparisons for single image: %s" % (np.mean(times))

times = []
for iter in range(0, 1000):
    start = time.time()
    number_comparisons = count_existing_comparisons()
    end = time.time()
    times.append(end - start)
time_log["count_existing_comparisons_all"] = np.mean(times)
print "count_existing_comparisons for all images: %s" % (np.mean(times))


# Get existing comparisons
times = []
for iter in range(0, 1000):
    start = time.time()
    comparisons = get_existing_comparisons(pk1=8)
    end = time.time()
    times.append(end - start)
time_log["get_existing_comparisons_single"] = np.mean(times)
print "get_existing_comparisons for single image: %s" % (np.mean(times))

times = []
for iter in range(0, 1000):
    start = time.time()
    comparisons = get_existing_comparisons()
    end = time.time()
    times.append(end - start)
time_log["get_existing_comparisons_all"] = np.mean(times)
print "get_existing_comparisons for all images: %s" % (np.mean(times))


# Count images processing
times = []
for iter in range(0, 1000):
    start = time.time()
    processing = count_possible_comparisons(pk1=8)
    end = time.time()
    times.append(end - start)
time_log["count_possible_comparisons_single"] = np.mean(times)
print "count_possible_comparisons for single image: %s" % (np.mean(times))

times = []
for iter in range(0, 1000):
    start = time.time()
    processing = count_possible_comparisons()
    end = time.time()
    times.append(end - start)
time_log["count_possible_comparisons_all"] = np.mean(times)
print "count_possible_comparisons for all images: %s" % (np.mean(times))


# SAVED LOG to compare with times from previous times
scripts_directory = os.path.abspath(os.path.join(afqvault.settings.BASE_DIR, "..", "scripts"))
number_images = Image.objects.all().count()

if os.path.exists("%s/time_log.pkl" % (scripts_directory)):
    log = pandas.read_pickle("%s/time_log.pkl" % (scripts_directory))
    last_entry = log.loc[log.index[log.shape[0] - 1]]
    tests_in_common = [x for x in last_entry.keys().tolist() if x in time_log.keys()]

    # Print change in tests that existed last time
    print "Last test was saved on %s, with %s images" % (last_entry["date"], last_entry["number_images"])
    for test in tests_in_common:
        if last_entry[test] is not None:
            print "%s: change is %s" % (test, time_log[test] - last_entry[test])

    # Add new tests to the table (not yet tested)
    new_tests = [t for t in time_log.keys() if t not in log.columns]
    if len(new_tests) > 0:
        for test in new_tests:
            log[test] = None

    now = time.strftime("%d-%m-%Y")
    log.loc[now, time_log.keys()] = time_log.values() + [now, number_images]

else:
    log = pandas.DataFrame(columns=time_log.keys() + ["date", "number_images"])
    now = time.strftime("%d-%m-%Y")
    log.loc[now] = time_log.values() + [now, number_images]

log.to_pickle("%s/time_log.pkl" % (scripts_directory))
