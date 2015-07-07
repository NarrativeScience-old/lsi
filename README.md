## LSI

The `lsi` command provides an easy way to rapidly query AWS to find information
about an instance, SSH onto it, or run an SSH command on multiple hosts in
parallel.

#### Instance search

Searching for an instance is exceedingly easy. Simply type `lsi` followed by
zero or more filters, which are substrings of an instance's name, IP address,
or other identifying information:

```
> lsi stg database
+---------------------------------------|-----------+
| Instance Name                         | Public IP |
| database-data-stg-1                   | 10.0.1.2  |
| database-data-stg-2                   | 10.0.1.2  |
| database-data-stg-3                   | 10.0.1.2  |
| database-services-stg-1               | 10.0.1.2  |
| database-services-stg-2               | 10.0.1.2  |
| database-services-stg-3               | 10.0.1.2  |
| stg-database-config-server-i-153dc5e9 | 10.0.1.2  |
| stg-database-config-server-i-1d21dcf5 | 10.0.1.2  |
| stg-database-config-server-i-2bd0d1c5 | 10.0.1.2  |
+---------------------------------------|-----------+
```

You can provide exclusionary filters with `-v`:

```
> lsi stg database -v services
+---------------------------------------|-----------+
| Instance Name                         | Public IP |
| database-rs-data-stg-1                | 10.0.1.2  |
| database-rs-data-stg-2                | 10.0.1.2  |
| database-rs-data-stg-3                | 10.0.1.2  |
| stg-database-config-server-i-153dc5e9 | 10.0.1.2  |
| stg-database-config-server-i-1d21dcf5 | 10.0.1.2  |
| stg-database-config-server-i-2bd0d1c5 | 10.0.1.2  |
+---------------------------------------|-----------+
```

The table by default will consist only of machine names and public IPs. You
can pull up additional information by passing the `--show` argument:


```
> lsi stg database --show private_ip
+---------------------------------------|-----------|------------+
| Instance Name                         | Public IP | Private IP |
| database-rs-data-stg-1                | 10.0.1.2  | 10.0.1.2   |
| database-rs-data-stg-2                | 10.0.1.2  | 10.0.1.2   |
| database-rs-data-stg-3                | 10.0.1.2  | 10.0.1.2   |
| database-rs-services-stg-1            | 10.0.1.2  | 10.0.1.2   |
| database-rs-services-stg-2            | 10.0.1.2  | 10.0.1.2   |
| database-rs-services-stg-3            | 10.0.1.2  | 10.0.1.2   |
| stg-database-config-server-i-153dc5e9 | 10.0.1.2  | 10.0.1.2   |
| stg-database-config-server-i-1d21dcf5 | 10.0.1.2  | 10.0.1.2   |
| stg-database-config-server-i-2bd0d1c5 | 10.0.1.2  | 10.0.1.2   |
+---------------------------------------|-----------|------------+
```

You can see all of the things that are available to show by requesting
`--attributes`:

```
> lsi --attributes
The following attributes are available: logical_id, ami_id, name, tags, stack_name, hostname, launch_time, public_ip, instance_type, private_ip, stack_id, security_groups
```

#### SSH onto an instance

Often the reason for searching in the first place is to SSH onto one of the
instances you find. Rather than copy/pasting manually, you can do this directly
from `lsi` using the `--ssh` or `-s` flag:

```
> lsi -s stg database data
+---|---------------------|-------------------------------------------|---------------+
|   | Instance Name       | Hostname                                  | Public IP     |
| 0 | database-data-stg-1 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 1 | database-data-stg-2 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 2 | database-data-stg-3 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
+---|---------------------|-------------------------------------------|---------------+
3 matching entries.
Commands:
  <n>: Connect to the nth instance in the list
  u username: Change SSH username to username (currently none set)
  i idfile: Change identity file to idfile (currently none set)
  f <one or more patterns>: Restrict results to those with patterns
  e <one or more patterns>: Restrict results to those without patterns
  c <command>: Set ssh command to run on matching hosts (currently none set)
  x: Execute the above command on the above host(s)
  q: Quit
Enter command:
```

At this point, you can enter the number of the instance you want to SSH onto,
which will immediately SSH you onto a machine.

Of course, you might not have permissions onto a machine with your own
username, or you might want to log in as another user or with a specific
identity file. You can do this with `--username` (`-u`) and `--identity-file`
(`-i`), respectively. If you do this, you don't need to pass the `-s` flag.

```
> lsi -u someuser -i ~/.ssh/somekey.pem stg database data
+---|---------------------|-------------------------------------------|---------------+
|   | Instance Name       | Hostname                                  | Public IP     |
| 0 | database-data-stg-1 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 1 | database-data-stg-2 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 2 | database-data-stg-3 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
+---|---------------------|-------------------------------------------|---------------+
3 matching entries.
Commands:
  <n>: Connect to the nth instance in the list
  u username: Change SSH username to username (currently someuser)
  i idfile: Change identity file to idfile (currently /home/anelson/.ssh/somekey.pem)
  f <one or more patterns>: Restrict results to those with patterns
  e <one or more patterns>: Restrict results to those without patterns
  c <command>: Set ssh command to run on matching hosts (currently none set)
  x: Execute the above command on the above host(s)
  q: Quit
Enter command:
```

#### Running SSH commands across instances

You can use `lsi` to execute an SSH command remotely on one or more instances.
To do this, use the `--command` (`-c`) option. Enter `x` at the confirmation
screen.

```
> lsi -c hostname stg database data
+---|---------------------|-------------------------------------------|---------------+
|   | Instance Name       | Hostname                                  | Public IP     |
| 0 | database-data-stg-1 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 1 | database-data-stg-2 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 2 | database-data-stg-3 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
+---|---------------------|-------------------------------------------|---------------+
3 matching entries.
Commands:
  <n>: Connect to the nth instance in the list
  u username: Change SSH username to username (currently none set)
  i idfile: Change identity file to idfile (currently none set)
  f <one or more patterns>: Restrict results to those with patterns
  e <one or more patterns>: Restrict results to those without patterns
  c <command>: Set ssh command to run on matching hosts (currently hostname)
  x: Execute the above command on the above host(s)
  q: Quit
Enter command: x
Running command `hostname` on 3 matching hosts
[database-data-stg-2 (10.0.1.2)]: ip-10.0.1.2
[database-data-stg-3 (10.0.1.2)]: ip-10.0.1.2
[database-data-stg-1 (10.0.1.2)]: ip-10.0.1.2
All commands finished
```

#### Profiles

It can be a bit tedious to enter extensive command-line arguments, especially
if they are the same over and over again. To alleviate this, you can create
*profiles* for LSI, which are collections of configuration. For example, you
can create a `someuser` profile which uses the `someuser` username and appropriate
keyfile. To do this, add a section to `.lsi`, which is written in the `ini`
format. For example:

```ini
[someuser]
username=someuser
identity file=~/.ssh/somekey.pem
```

You can then invoke your profile with `--profile` (`-p`):

```
> lsi -p someuser stg database data
+---|---------------------|-------------------------------------------|---------------+
|   | Instance Name       | Hostname                                  | Public IP     |
| 0 | database-data-stg-1 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 1 | database-data-stg-2 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
| 2 | database-data-stg-3 | ec2-W-X-Y-Z.compute-1.amazonaws.com       | 10.0.1.2      |
+---|---------------------|-------------------------------------------|---------------+
3 matching entries.
Commands:
  <n>: Connect to the nth instance in the list
  u username: Change SSH username to username (currently someuser)
  i idfile: Change identity file to idfile (currently /home/anelson/.ssh/somekey.pem)
  f <one or more patterns>: Restrict results to those with patterns
  e <one or more patterns>: Restrict results to those without patterns
  c <command>: Set ssh command to run on matching hosts (currently none set)
  x: Execute the above command on the above host(s)
  q: Quit
Enter command:
```

Profiles can inherit from other profiles, allowing you to avoid repetition. For
example, you might put the entire above command into a profile:

```ini
[someuser]
username=someuser
identity file=~/.ssh/somekey.pem

[stg-database]
inherits=someuser
filters=stg,database,data
```

Then the `lsi -p stg-database` command will be equivalent to the above.


## Installation


#### Via `pip`:


```bash
$ pip install lsi
```