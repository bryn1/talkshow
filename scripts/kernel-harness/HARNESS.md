# kernel-lab HARNESS.md — MC 12422 / card 12404.2.1 (blcc-kernel milestone M0a)

Purpose: prove the testbed BEFORE blcc touches a kernel file — a reference **gcc** build of
upstream-unmodified linux-5.10 that **boots in QEMU with a busybox initramfs printing the
sentinel `BLCC-HARNESS-OK`**. Everything lives under `/home/claudecode/Blaha/kernel-lab/`.
`/home/claudecode/Blaha/c-compiler` was never written to (`git status --porcelain` empty, verified twice).

Rollback of this harness: delete `/home/claudecode/Blaha/kernel-lab/`; apt packages removed with
`sudo -n apt-get remove -y qemu-system-x86 flex bison bc libelf-dev libssl-dev` (nothing else on the
host was configured or changed).

## Host + toolchain (leg 1)

Ubuntu 22.04 (VM350), all commands run by user `claudecode`.

```
sudo -n DEBIAN_FRONTEND=noninteractive apt-get install -y qemu-system-x86 flex bison bc libelf-dev libssl-dev   # exit 0
# full transcript: evidence/apt-install.log
```

Versions after install:

| tool | version |
|---|---|
| gcc | 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3), /usr/bin/gcc |
| qemu-system-x86_64 | QEMU emulator version 6.2.0 (Debian 1:6.2+dfsg-2ubuntu6.31) |
| flex | 2.6.4 |
| bison | (GNU Bison) 3.8.2 |
| bc | 1.07.1 |
| libelf-dev | 0.186-1ubuntu0.1 |
| libssl-dev | 3.0.2-0ubuntu1.30 |

## Kernel (leg 2)

- Listing: `curl -s https://cdn.kernel.org/pub/linux/kernel/v5.x/ | grep -oE 'linux-5\.10\.[0-9]+\.tar\.xz' | sort -uV | tail`
  → highest present: **5.10.274** (contiguous tail of the listing: .267 … .274).
- **Deviation from brief:** the brief's sanity range said 200..260; the actual highest is 274.
  Reading used: "picking the highest N you see" wins — the contiguous series and the live listing
  prove the parse; the brief's range was stale. Documented here, not silently chosen.
- Download + hash:

```
cd /home/claudecode/Blaha/kernel-lab
curl -fsS -O https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.10.274.tar.xz
curl -fsS -o sha256sums.asc https://cdn.kernel.org/pub/linux/kernel/v5.x/sha256sums.asc
sha256sum linux-5.10.274.tar.xz
# 9f87a8b523560ca7740ea4a149c6dc0dab7814c2a41bccdb739b291a7e120b8c  linux-5.10.274.tar.xz
# MATCHES kernel.org sha256sums.asc (independently grepped). Also stored in tarball-sha256.txt.
tar -xf linux-5.10.274.tar.xz && mv linux-5.10.274 linux-5.10   # tree root = kernel-lab/linux-5.10/Makefile
```

- Tree state: **upstream sources unmodified**. Only build products + `.config` exist in-tree
  (in-tree build was mandated by the brief: `make tinyconfig && make vmlinux`).
- Kernel Makefile stamps: VERSION=5 PATCHLEVEL=10 SUBLEVEL=274.

## BusyBox initramfs (leg 3)

- Latest stable 1.36.x on https://busybox.net/downloads/ = **1.36.1**.

```
cd /home/claudecode/Blaha/kernel-lab
curl -fsS -O https://busybox.net/downloads/busybox-1.36.1.tar.bz2
sha256sum busybox-1.36.1.tar.bz2
# b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314  busybox-1.36.1.tar.bz2  (also busybox-sha256.txt)
tar -xf busybox-1.36.1.tar.bz2
cd busybox-1.36.1
make defconfig
sed -i 's/^# CONFIG_STATIC is not set$/CONFIG_STATIC=y/' .config
make silentoldconfig        # see substitution table below (brief said olddefconfig)
make -j12                   # exit 0; result: ELF 64-bit static executable ("not a dynamic executable")
make CONFIG_PREFIX=/home/claudecode/Blaha/kernel-lab/initramfs-root install
```

- **Substitution:** BusyBox kconfig has **no `olddefconfig` target** (`No rule to make target
  'olddefconfig'`). `make silentoldconfig` is its non-interactive equivalent ("using defaults
  found in .config"). menuconfig never invoked.
- Banner: `BusyBox v1.36.1 (2026-11-12 12:46:13 UTC) multi-call binary.`

### /init (chmod +x, shebang #!/bin/sh)

```sh
#!/bin/sh
mount -t devtmpfs devtmpfs /dev
mount -t proc proc /proc 2>/dev/null
echo BLCC-HARNESS-OK
exec /bin/sh 0</dev/console 1>/dev/console 2>/dev/console
```

(The console-redirection trio per the brief; `mount -t proc` added — proc is needed by common
tooling and is harmless. `/bin/sh` is busybox, static.)

### rootfs

```
cd /home/claudecode/Blaha/kernel-lab/initramfs-root
mkdir -p dev proc tmp root sys
find . | cpio -o -H newc | gzip > ../rootfs.cpio.gz
```

Layout of `initramfs-root/` (414 entries): `bin/` (busybox + ~230 applet symlinks, `bin/busybox`
static ELF64), `sbin/`, `usr/`, `init`, `linuxrc`, `dev/ proc/ sys/ tmp/ root/` (empty mount dirs).
`rootfs.cpio.gz` = 1309103 bytes.

## Kernel reference build (leg 4) — in-tree, gcc 11.4

```
cd /home/claudecode/Blaha/kernel-lab/linux-5.10
make tinyconfig                                        # exit 0
cp .config ../evidence/config-tinyconfig.baseline      # pre-change baseline for the diff
./scripts/config --enable DEVTMPFS --enable DEVTMPFS_MOUNT --enable SERIAL_8250_CONSOLE \
                  --enable VT --enable BINFMT_SCRIPT --enable VIRTIO_PCI --enable VIRTIO_BLK --enable TMPFS
# + dependency enables the tinyconfig context actually requires (table below):
./scripts/config --enable TTY --enable SERIAL_8250 --enable BLOCK --enable BLK_DEV \
                  --enable PCI --enable SHMEM --enable VIRTIO --enable VIRTIO_MENU \
                  --enable SYSFS --enable PRINTK
# BINFMT_ELF: scripts/config worked; 64BIT: scripts/config --enable 64BIT
echo 'CONFIG_PVH=y' >> .config   # attempted, see PVH note; olddefconfig drops it
make olddefconfig                # repeatedly; exit 0
diff -u ../evidence/config-tinyconfig.baseline .config > ../evidence/config-tinyconfig.diff  # 1241 lines
make -j12 vmlinux                # exit 0  (also built target: bzImage, needed for boot, see below)
make -j12 vmlinux bzImage        # final build exit 0; vmlinux 12668416 B ELF64 @ linux-5.10/vmlinux
```

### Config substitutions vs the brief's list (tinyconfig = allnoconfig + EXPERT, so every
### dependency must be spelled out — symbols the brief names are DROPPED by olddefconfig unless
### their depends chain is enabled too). Final .config has ALL of these =y:

| brief symbol | extra enables needed under tinyconfig (why) |
|---|---|
| SERIAL_8250_CONSOLE | `TTY`, `SERIAL_8250` (console depends on the 8250 driver, which depends on TTY) |
| VIRTIO_PCI | `PCI`, `VIRTIO`, `VIRTIO_MENU` (depends on PCI; tristate gated by the Virtio-drivers menu) |
| VIRTIO_BLK | `VIRTIO` + `VIRTIO_MENU` |
| TMPFS | `SHMEM` (TMPFS depends on SHMEM) |
| DEVTMPFS / DEVTMPFS_MOUNT | `SYSFS` kept =y (sysfs is standard; DEVTMPFS_MOUNT also needs BLK_DEV_INITRD) |
| (initramfs unpack) | `BLK_DEV_INITRD` — NOT enabled by tinyconfig; without it the -initrd is ignored |
| (block layer for VIRTIO_BLK) | `BLOCK`, `BLK_DEV` (BLK_DEV depends on BLOCK) |
| (console output at all) | `PRINTK` — tinyconfig disables printk, no evidence would print |
| (exec any binary) | **`BINFMT_ELF`** — tinyconfig disables the ELF loader; symptom: `Failed to execute /init (error -8)` ENOEXEC even for a valid static ELF. The brief's `BINFMT_SCRIPT` alone is not enough. |
| **`64BIT`** | **CRITICAL:** `make tinyconfig` yields a **32-bit (i386) kernel** (`# CONFIG_64BIT is not set`); a static ELF64 busybox then fails elf_check_arch → `/init` error -8 again. Enable `CONFIG_64BIT=y` for an x86_64 kernel ("boot to /bin/sh from initramfs on ttyS0" on qemu-system-x86_64 requires it). |
| `CONFIG_PVH` | attempted for `-kernel vmlinux` boot: kconfig silently DROPS it in this tree (not even `# CONFIG_PVH is not set` appears after `make olddefconfig`; verified pre- and post-64BIT). See boot note. |

## Boot proof (leg 5)

**Command used (canonical, produced `evidence/gcc-boot.log`):**

```
cd /home/claudecode/Blaha/kernel-lab
timeout 120 qemu-system-x86_64 -machine q35 -m 1024 -nographic -no-reboot \
  -kernel /home/claudecode/Blaha/kernel-lab/linux-5.10/arch/x86/boot/bzImage \
  -initrd /home/claudecode/Blaha/kernel-lab/rootfs.cpio.gz \
  -append "console=ttyS0" > evidence/gcc-boot.log 2>&1
# QEMU_EXIT=124  (expected: timeout kills the console-waiting sh; the brief pre-declares 124 fine)
# grep -c BLCC-HARNESS-OK evidence/gcc-boot.log  =>  1
```

**Substitution (debugged, not guessed):** the brief's `-kernel .../vmlinux` fails on
QEMU 6.2/q35: `qemu-system-x86_64: Error loading uncompressed kernel without PVH ELF Note`.
The 5.10 fix-path `CONFIG_PVH` is not selectable in this tree (olddefconfig deletes it).
Direct ELF `-kernel` boot therefore goes through **`arch/x86/boot/bzImage`** — the standard
QEMU kernel artifact built from the SAME tree/config/`make -j12 vmlinux bzImage` run.
`linux-5.10/vmlinux` (the card probe artifact) remains built and untouched at the pinned path
(ELF64, 12668416 B).

Boot evidence in log: `Linux version 5.10.274 (gcc 11.4.0) #2 SMP`, `Run /init as init process`,
`BLCC-HARNESS-OK` on console, no panic; exit 124 from timeout as expected.

## Artifacts (pinned paths, card probes)

| path | what |
|---|---|
| `kernel-lab/linux-5.10/vmlinux` | 64-bit reference vmlinux, gcc 11.4, from unmodified 5.10.274 sources |
| `kernel-lab/linux-5.10/arch/x86/boot/bzImage` | same build, boot artifact for QEMU `-kernel` |
| `kernel-lab/rootfs.cpio.gz` | busybox-1.36.1 static initramfs, /init prints sentinel |
| `kernel-lab/evidence/gcc-boot.log` | real QEMU console transcript, contains BLCC-HARNESS-OK |
| `kernel-lab/evidence/config-tinyconfig.baseline` | .config immediately after `make tinyconfig` |
| `kernel-lab/evidence/config-tinyconfig.diff` | tinyconfig → final .config (1241 lines) |
| `kernel-lab/evidence/apt-install.log` | leg-1 apt transcript |
| `kernel-lab/evidence/m0a-verdict.md` | leg-by-leg verdict file (VERIFY_EXIT + PROBE + VERDICT) |
| `kernel-lab/tarball-sha256.txt`, `busybox-sha256.txt`, `sha256sums.asc` | hashes |

Known limits (for the record): initramfs cpio carries uid 1000 (built as unprivileged user;
harmless — kernel unpacks initramfs owned as-is and runs /init as uid 0); root is the initramfs
(tmpfs), no disk image; single console ttyS0 only; VT enabled per brief but unused by this boot.
