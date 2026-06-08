# Known Issues

The folllowing is a list of known issues that can cause issues during use of ARM, with potential work arounds.

## Ripping

* **Issue:** If the host running the container mid-job, any data that wasn't at rest is lost. Additionally, the job logic will be lest in a broken state and must be deleted.
**Solution:** abandon the old job and start a new rip.

* **Issue:** Movies with a `/` in the name can break the rip.
**Solution:** none at present

* **Issue:** SQLite has a read / write limit, depending on ARM use the database can enter a state where ripping fails due to an inability to read or write data to the database. 
**Solution:** planned for resolution in 3.x [Development Path](Status-Roadmap)

* **Issue:** Ubuntu kernel 5.15.134 is known to break ARM per #1353
**Solution:** Upgrade host Ubuntu system to a later kernel

```bash
Mar 25 16:55:30 ripperbox kernel: UDF-fs: error (device sr5): udf_fiiter_advance_blk: extent after position 2016 not allocated in directory (ino 269)
Mar 25 16:55:30 ripperbox kernel: UDF-fs: error (device sr5): udf_verify_fi: directory (ino 269) has entry where CRC length (36) does not match entry length (240)
```

## User Iterface

* Running in dark mode can cause some of the text and boxes to not display correctly
