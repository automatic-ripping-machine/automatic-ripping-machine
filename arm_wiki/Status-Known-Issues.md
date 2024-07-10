# Known Issues

The following is a list of known issues relating to ARM:

* If the host running the container mid-job, any data that wasn't at rest is lost. Additionally, the job logic will be lest in a broken state and must be deleted.
* Movies with a `/` in the name can break the rip
* SQLite has a read / write limit, depending on ARM use the database can enter a state where ripping fails due to an inability to read or write data to the database. (resolved in 3.x)