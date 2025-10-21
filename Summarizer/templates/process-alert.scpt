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
		on error errMsg
			display notification "Failed to save alert: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		-- Run Python pipeline with SMTP sending (no UI automation needed)
		try
			-- Use Homebrew python3 explicitly (Mail.app's 'which' may find Xcode's python)
			set pythonPath to "/usr/local/bin/python3"

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

			-- Run pipeline with --smtp-send flag to send digest via SMTP
			-- Topic extraction now handled by Python (reads from alert.eml)
			set pythonCmd to "cd " & quoted form of repoPath & " && " & pythonPath & " -m Summarizer.cli run --output-dir " & quoted form of outputDir & " --email-digest " & quoted form of digestRecipient & " --smtp-send 2>&1"
			do shell script pythonCmd

			-- Notify success
			display notification "Google Alert digest sent to " & digestRecipient with title "Google Alert Intelligence" sound name "Glass"
		on error errMsg
			display notification "Pipeline failed: " & errMsg with title "Google Alert Intelligence"
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
