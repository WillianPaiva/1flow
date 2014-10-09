from bson import json_util
import json

print json.dumps(db.admin.command('getCmdLineOpts'),
                 indent=4, default=json_util.default)
{
    "ok": 1.0,
    "parsed": {
        "storage": {
            "dbPath": "/var/lib/mongodb"
        },
        "net": {
            "bindIp": "127.0.0.1"
        },
        "config": "/etc/mongodb.conf",
        "systemLog": {
            "path": "/var/log/mongodb/mongod.log",
            "destination": "file",
            "logAppend": true,
            "quiet": true
        }
    },
    "argv": [
        "/usr/bin/mongod",
        "--quiet",
        "--config",
        "/etc/mongodb.conf"
    ]
}

————————————————————————————————————————————————————————————————————————————————


print json.dumps(db.admin.command('serverStatus'),
                 indent=4, default=json_util.default)
{
    "ok": 1.0,
    "parsed": {
        "storage": {
            "dbPath": "/var/lib/mongodb"
        },
        "net": {
            "bindIp": "127.0.0.1"
        },
        "config": "/etc/mongodb.conf",
        "systemLog": {
            "path": "/var/log/mongodb/mongod.log",
            "destination": "file",
            "logAppend": true,
            "quiet": true
        }
    },
    "argv": [
        "/usr/bin/mongod",
        "--quiet",
        "--config",
        "/etc/mongodb.conf"
    ]
}

————————————————————————————————————————————————————————————————————————————————

print json.dumps(db.oneflow_dev.command('dbstats'),
                 indent=4, default=json_util.default)
{
    "extentFreeList": {
        "totalSize": 0,
        "num": 0
    },
    "storageSize": 458752,
    "ok": 1.0,
    "avgObjSize": 709.7358490566038,
    "dataFileVersion": {
        "major": 4,
        "minor": 5
    },
    "db": "oneflow_dev",
    "indexes": 37,
    "objects": 371,
    "collections": 12,
    "fileSize": 67108864,
    "numExtents": 17,
    "dataSize": 263312,
    "indexSize": 318864,
    "nsSizeMB": 16
}

————————————————————————————————————————————————————————————————————————————————

print json.dumps(db.oneflow_dev.command('collStats', 'article'),
                 indent=4, default=json_util.default)
{
    "count": 70,
    "ns": "oneflow_dev.article",
    "ok": 1.0,
    "lastExtentSize": 131072,
    "avgObjSize": 1783,
    "totalIndexSize": 81760,
    "systemFlags": 1,
    "userFlags": 1,
    "numExtents": 3,
    "nindexes": 8,
    "storageSize": 172032,
    "indexSizes": {
        "url_error_1": 8176,
        "date_published_1": 8176,
        "content_type_1": 8176,
        "_id_": 8176,
        "url_1": 24528,
        "duplicate_of_1": 8176,
        "source_1": 8176,
        "content_error_1": 8176
    },
    "paddingFactor": 1.1210000000000178,
    "size": 124832
}

————————————————————————————————————————————————————————————————————————————————

print json.dumps(db.admin.command('hostInfo'),
                 indent=4, default=json_util.default)
{
    "ok": 1.0,
    "os": {
        "version": "Kernel 3.16.3-1-ARCH",
        "type": "Linux",
        "name": "NAME=\"Arch Linux\""
    },
    "system": {
        "cpuAddrSize": 64,
        "numCores": 4,
        "currentTime": {
            "$date": 1412828254669
        },
        "hostname": "Chani",
        "cpuArch": "x86_64",
        "numaEnabled": false,
        "memSizeMB": 7905
    },
    "extra": {
        "kernelVersion": "3.16.3-1-ARCH",
        "numPages": 2023853,
        "pageSize": 4096,
        "maxOpenFiles": 1024,
        "versionString": "Linux version 3.16.3-1-ARCH (nobody@var-lib-archbuild-testing-x86_64-tobias) (gcc version 4.9.1 20140903 (prerelease) (GCC) ) #1 SMP PREEMPT Wed Sep 17 21:54:13 CEST 2014",
        "libcVersion": "2.20",
        "cpuFeatures": "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf eagerfpu pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm ida arat epb xsaveopt pln pts dtherm tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid",
        "cpuFrequencyMHz": "2071.687"
    }
}
