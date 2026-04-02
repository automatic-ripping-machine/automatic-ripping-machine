// mount-helper is a privileged daemon that runs as root and accepts
// mount/umount/eject requests for optical drives (/dev/sr*) over a
// unix socket. This allows unprivileged processes to manage disc mounts
// without suid binaries, so you can use Docker's no-new-privileges
// option.
//
// Only these exact command forms are accepted:
//
//   mount [--source] /dev/srN
//   umount /dev/srN
//   eject --verbose --cdrom --scsi [--trayclose|--traytoggle] /dev/srN
package main

import (
	"bufio"
	"fmt"
	"net"
	"os"
	"os/exec"
	"os/user"
	"regexp"
	"strconv"
	"strings"
)

const socketPath = "/run/mount-helper.sock"

var devicePattern = regexp.MustCompile(`^/dev/sr\d+$`)

func handleRequest(line string) string {
	args := strings.Fields(line)
	if len(args) == 0 {
		return "ERROR: empty request"
	}

	cmd := args[0]
	rest := args[1:]

	switch cmd {
	case "mount":
		return handleMount(rest)
	case "umount":
		return handleUmount(rest)
	case "eject":
		return handleEject(rest)
	default:
		return "ERROR: unknown command"
	}
}

func handleMount(args []string) string {
	// mount --source /dev/srN
	// mount /dev/srN
	var device string
	switch len(args) {
	case 1:
		device = args[0]
	case 2:
		if args[0] != "--source" {
			return "ERROR: invalid mount flag"
		}
		device = args[1]
	default:
		return "ERROR: invalid mount arguments"
	}

	if !devicePattern.MatchString(device) {
		return "ERROR: invalid device"
	}
	return run("/bin/mount", args...)
}

func handleUmount(args []string) string {
	// umount /dev/srN
	if len(args) != 1 || !devicePattern.MatchString(args[0]) {
		return "ERROR: invalid umount arguments"
	}
	return run("/bin/umount", args[0])
}

func handleEject(args []string) string {
	// eject --verbose --cdrom --scsi [--trayclose|--traytoggle] /dev/srN
	if len(args) < 1 {
		return "ERROR: invalid eject arguments"
	}

	device := args[len(args)-1]
	if !devicePattern.MatchString(device) {
		return "ERROR: invalid device"
	}

	flags := args[:len(args)-1]
	allowed := map[string]bool{
		"--verbose":    true,
		"--cdrom":      true,
		"--scsi":       true,
		"--trayclose":  true,
		"--traytoggle": true,
	}
	for _, f := range flags {
		if !allowed[f] {
			return fmt.Sprintf("ERROR: invalid eject flag: %s", f)
		}
	}
	return run("/usr/bin/eject", args...)
}

func run(bin string, args ...string) string {
	cmd := exec.Command(bin, args...)
	cmd.Stdin = nil
	output, err := cmd.CombinedOutput()
	if err != nil {
		msg := strings.TrimSpace(string(output))
		if msg != "" {
			return "ERROR: " + msg
		}
		return "ERROR: " + err.Error()
	}
	return "OK"
}

func logf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, "mount-helper: "+format+"\n", args...)
}

func handleConn(conn net.Conn) {
	defer conn.Close()
	scanner := bufio.NewScanner(conn)
	if scanner.Scan() {
		request := scanner.Text()
		logf("request: %s", request)
		response := handleRequest(request)
		logf("response: %s", response)
		fmt.Fprintln(conn, response)
	} else {
		logf("no input received")
	}
}

func main() {
	os.Remove(socketPath)

	listener, err := net.Listen("unix", socketPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "mount-helper: %v\n", err)
		os.Exit(1)
	}
	defer listener.Close()

	if err := os.Chmod(socketPath, 0660); err != nil {
		fmt.Fprintf(os.Stderr, "mount-helper: chmod: %v\n", err)
		os.Exit(1)
	}
	armUser, err := user.Lookup("arm")
	if err != nil {
		fmt.Fprintf(os.Stderr, "mount-helper: lookup arm user: %v\n", err)
		os.Exit(1)
	}
	uid, _ := strconv.Atoi(armUser.Uid)
	gid, _ := strconv.Atoi(armUser.Gid)
	if err := os.Chown(socketPath, uid, gid); err != nil {
		fmt.Fprintf(os.Stderr, "mount-helper: chown: %v\n", err)
		os.Exit(1)
	}

	fmt.Fprintf(os.Stderr, "mount-helper listening on %s\n", socketPath)

	for {
		conn, err := listener.Accept()
		if err != nil {
			fmt.Fprintf(os.Stderr, "mount-helper: accept: %v\n", err)
			continue
		}
		go handleConn(conn)
	}
}
