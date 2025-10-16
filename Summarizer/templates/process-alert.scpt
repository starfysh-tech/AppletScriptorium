using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		-- Generate timestamp for output directory
		set timestamp to do shell script "date +%Y%m%d-%H%M%S"
		set outputDir to (POSIX path of (path to home folder)) & "Code/AppletScriptorium/runs/alert-" & timestamp

		-- Get absolute path to home directory
		set homePath to POSIX path of (path to home folder)
		set repoPath to homePath & "Code/AppletScriptorium"

		-- Get recipient (customize this as needed)
		set digestRecipient to "{{EMAIL}}"

		-- Create output directory and save the triggering message
		try
			do shell script "mkdir -p " & quoted form of outputDir
			set alertEmlPath to outputDir & "/alert.eml"
			set triggerMessage to item 1 of theMessages
			set messageSource to source of triggerMessage
			my write_text_to_file(messageSource, alertEmlPath)

			-- Extract topic from alert subject (e.g., "Google Alert - Medication reminder" → "Medication reminder")
			set alertSubject to subject of triggerMessage
			set topicName to ""
			if alertSubject contains "Google Alert - " then
				set topicName to text ((offset of "Google Alert - " in alertSubject) + 15) thru -1 of alertSubject
			else
				set topicName to "Unknown"
			end if
		on error errMsg
			display notification "Failed to save alert: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		-- Run Python pipeline (using system Python - creates digest.html and digest.eml)
		try
			-- Resolve python3 path dynamically
			set pythonPath to do shell script "which python3 2>/dev/null || echo '/usr/local/bin/python3'"

			-- Verify Python 3.11+ is available
			try
				set pythonVersion to do shell script pythonPath & " --version 2>&1"
				if pythonVersion does not contain "Python 3." then
					display notification "Python 3 not found at: " & pythonPath with title "Google Alert Intelligence"
					return
				end if
			on error
				display notification "Python 3 not found. Install via Homebrew: brew install python3" with title "Google Alert Intelligence"
				return
			end try

			set pythonCmd to "cd " & quoted form of repoPath & " && " & pythonPath & " -m Summarizer.cli run --output-dir " & quoted form of outputDir & " --email-digest " & quoted form of digestRecipient
			do shell script pythonCmd
		on error errMsg
			display notification "Pipeline failed: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		-- Prepare paths
		set emlPath to outputDir & "/digest.eml"
		set emlFileURL to "file://" & emlPath

		-- Step 1: Open .eml file to render HTML
		try
			do shell script "open " & quoted form of emlPath
			delay 4
		on error errMsg
			display notification "Could not open .eml file: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		-- Step 2: Copy rendered HTML from .eml viewer
		tell application "Mail"
			activate
			delay 1
		end tell

		try
			tell application "System Events"
				tell process "Mail"
					set frontmost to true
					keystroke "a" using command down
					delay 0.5
					keystroke "c" using command down
				end tell
			end tell
		on error errMsg
			display notification "Copy from viewer failed: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		delay 1

		-- Step 3: Close .eml viewer
		tell application "Mail"
			try
				close (front window)
			end try
		end tell

		delay 1

		-- Step 4: Create compose window with placeholder
		tell application "Mail"
			try
				set emailSubject to "Google Alert Summary - " & topicName & " - " & (do shell script "date '+%B %d, %Y'")
				set newMessage to make new outgoing message with properties {subject:emailSubject, content:"[PLACEHOLDER]", visible:true}
				tell newMessage
					make new to recipient with properties {address:digestRecipient}
				end tell
				activate
			on error errMsg
				display notification "Failed to create compose window: " & errMsg with title "Google Alert Intelligence"
				return
			end try
		end tell

		delay 2

		-- Step 5: Focus body field and paste
		try
			tell application "System Events"
				tell process "Mail"
					set frontmost to true
					set theWindow to front window
					set allElements to entire contents of theWindow

					-- Find AXWebArea (body field) and set focus
					repeat with elem in allElements
						try
							if role of elem is "AXWebArea" then
								set focused of elem to true
								delay 0.5
								keystroke "a" using command down
								delay 0.5
								keystroke "v" using command down
								exit repeat
							end if
						end try
					end repeat
				end tell
			end tell
		on error errMsg
			display notification "Paste failed: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		delay 3

		-- Step 6: Send the message with Cmd+Shift+D
		try
			tell application "System Events"
				tell process "Mail"
					set frontmost to true
					keystroke "d" using {command down, shift down}
				end tell
			end tell

			delay 3

			-- Verify window closed (successful send)
			tell application "Mail"
				set openWindows to every window
				set stillOpen to false

				repeat with w in openWindows
					try
						if name of w contains emailSubject then
							set stillOpen to true
							exit repeat
						end if
					end try
				end repeat

				if stillOpen then
					display notification "Message created but not sent - check Mail.app" with title "Google Alert Intelligence"
				else
					display notification "Google Alert digest sent to " & digestRecipient with title "Google Alert Intelligence" sound name "Glass"
				end if
			end tell
		on error errMsg
			display notification "Failed to send: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		-- Mark trigger email as read
		repeat with aMessage in theMessages
			set read status of aMessage to true
		end repeat
	end perform mail action with messages
end using terms from

on write_text_to_file(text_payload, posix_path)
	set file_alias to POSIX file posix_path
	set file_descriptor to open for access file_alias with write permission
	try
		set eof of file_descriptor to 0
		write text_payload to file_descriptor starting at 0
	on error err_text number err_num
		close access file_descriptor
		error err_text number err_num
	end try
	close access file_descriptor
end write_text_to_file
