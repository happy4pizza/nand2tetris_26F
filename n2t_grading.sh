#!/bin/bash
# Usage: n2t_grading.sh </path/to/project/folder>

# Default settings
VERBOSE=false
PROJECT_DIR=""
WINDOWS=false

usage() {
    echo "Usage: $0 [options] [/path/to/project/folder]"
    echo "If no project folder is specified, the current folder is used"
    echo "Options:"
    echo "  -v, --verbose       Enable verbose mode"
    echo "  -h, --help          Display this help message"
}

check_args() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
			-v|--verbose)
				VERBOSE=true
				shift
	            ;;
		    -h|--help)
			    usage
				exit 0
				;;
	        -*|--*)
		        echo "Unknown option: $1"
			    usage >&2
				exit 1
				;;
	        *)
		        # Check for a provided project dir
			    if [ -z "$PROJECT_DIR" ]; then
				    PROJECT_DIR="$1"
					shift
	            else
		            echo "Error: Multiple project folders provided"
			        usage
				fi
				;;
	    esac
	done

	# Use current dir if no project dir provided
	if [ -z "$PROJECT_DIR" ]; then
	    PROJECT_DIR="$PWD"
		echo "No project directory provided. Using current directory"
    fi
}

run_tests() {
	# Extract project number
	# Pull all tests, keeping subfolders
	local CLEAN_PATH="${PROJECT_DIR%/}"
	local PROJECT_NAME="${CLEAN_PATH##*/}"
	local PROJ_NUM=""

	if [[ "$PROJECT_NAME" =~ ^[0-9]+$ ]]; then
		PROJ_NUM=$(printf "%02d" "$((10#$PROJECT_NAME))")
	else
		echo "Error: Unrecognized project format"
	    exit 1
	fi

	# Select emulator/simulator based on project number
	local RUNNER=""
	case "$PROJ_NUM" in
		01|02|03|05)
			RUNNER="HardwareSimulator"
	        ;;
		07|08)
			RUNNER="VMEmulator"
	        ;;
		04|12)
			RUNNER="CPUEmulator"
	        ;;
		06|10|11)
			echo "Project $PROJ_NUM requires testing compiler/assembler outputs directly"
	        exit 0
		    ;;
		09)
			echo "Project $PROJ_NUM has no tests"
			exit 0
			;;
	    *)
			echo "Error: Project $PROJ_NUM test runner not found"
			exit 1
	        ;;
	esac

	# Check if running on windows
	# Windows uses the .bat runners, not .sh
	case "$OSTYPE" in
		msys*|cygwin*)
			WINDOWS=true
	esac

	if $WINDOWS; then
		RUNNER="${RUNNER}.bat"
	else
		RUNNER="${RUNNER}.sh"
	fi

	if $VERBOSE; then
		echo "Using $RUNNER test runner"
	fi

	# Open project folder or exit on fail
	cd "$CLEAN_PATH" || exit 1

	echo "================================"
	echo " Testing Nand2Tetris Project $PROJ_NUM"
	echo "================================"

	run_simulator_tests
}

run_simulator_tests() {
	local TOTAL_TESTS=0
	local PASSED_TESTS=0
	local FAILED_TESTS=0
	local SKIPPED_TESTS=0

	# Run every testfile in the folder
	local OUTPUT=""
	while IFS= read -r testfile; do
		# Remove leading ./
		testfile="${testfile#./}"

		# Ignore all tests that require user input
		case "$testfile" in
			*/Fill.tst|*Memory.tst)
				printf "[\e[33mSKIP\e[0m] %s\n" "$testfile"
				((SKIPPED_TESTS++))
				continue
				;;
		esac

		((TOTAL_TESTS++))

		# Check if output was successful
		OUTPUT="$("$RUNNER" "$testfile" 2>&1)"

		if echo "$OUTPUT" | grep -q "success"; then
			printf "[\e[32mPASS\e[0m] %s\n" "$testfile"
			((PASSED_TESTS++))
		else
			printf "[\e[31mFAIL\e[0m] %s\n" "$testfile"
			echo "$OUTPUT" | grep -i "failure"
			((FAILED_TESTS++))
		fi
	done < <(find . -type f -name "*.tst")

	echo "================================"
	echo "          $PASSED_TESTS / $TOTAL_TESTS passed         "
	if (( SKIPPED_TESTS > 0 )); then
		echo "           $SKIPPED_TESTS skipped            "
	fi
	echo "================================"

	if (( FAILED_TESTS == 0 )); then
		return 0
	else
		return 1
	fi
}


check_args "$@"

run_tests
exit $?
