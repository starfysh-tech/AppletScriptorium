using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		-- Log execution for debugging
		set homePath to POSIX path of (path to home folder)
		set logFile to homePath & "Code/AppletScriptorium/runs/mail-rule-execution.log"
		do shell script "echo \"$(date '+%Y-%m-%d %H:%M:%S') - Mail rule triggered\" >> " & quoted form of logFile

		-- Generate timestamp for output directory
		set timestamp to do shell script "date +%Y%m%d-%H%M%S"
		set outputDir to homePath & "Code/AppletScriptorium/runs/alert-" & timestamp

		-- Get absolute path to repository
		set repoPath to homePath & "Code/AppletScriptorium"

		-- Get recipient (customize this as needed)
		set digestRecipient to "{{EMAIL}}"

		-- Create output directory and save the triggering message
		try
			do shell script "mkdir -p " & quoted form of outputDir
			set alertEmlPath to outputDir & "/alert.eml"
			set triggerMessage to item 1 of theMessages

			-- Log email details for debugging
			set msgSubject to subject of triggerMessage
			set msgSender to sender of triggerMessage
			set logEntry to "$(date '+%Y-%m-%d %H:%M:%S') - Subject: " & quoted form of msgSubject & " | From: " & quoted form of msgSender
			do shell script "echo " & quoted form of logEntry & " >> " & quoted form of logFile

			-- Validate it's actually a Google Alert
			if msgSubject does not contain "Google Alert" then
				set warningEntry to "$(date '+%Y-%m-%d %H:%M:%S') - WARNING: Non-Google Alert email captured! Subject: " & quoted form of msgSubject
				do shell script "echo " & quoted form of warningEntry & " >> " & quoted form of logFile
			end if

			set messageSource to source of triggerMessage
			my write_text_to_file(messageSource, alertEmlPath)
		on error errMsg
			display notification "Failed to save alert: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		-- Run Python pipeline with SMTP sending (no UI automation needed)
		try
			-- Python path configured during setup (selected by user based on available installations)
			set pythonPath to "{{PYTHON_PATH}}"

			-- Run pipeline with --smtp-send flag to send digest via SMTP
			-- Topic extraction now handled by Python (reads from alert.eml)
			set pythonCmd to "cd " & quoted form of repoPath & " && PYTHONPATH=" & quoted form of repoPath & " " & pythonPath & " -m Summarizer.cli run --output-dir " & quoted form of outputDir & " --email-digest " & quoted form of digestRecipient & " --smtp-send 2>&1"
			do shell script pythonCmd

			-- Notify success
			display notification "Google Alert digest sent to " & digestRecipient with title "Google Alert Intelligence" sound name "Glass"
		on error errMsg
			-- Parse common error messages for better user feedback
			set errorSummary to errMsg
			if errMsg contains "not found - check .env" then
				set errorSummary to "LM Studio model not found - check .env LMSTUDIO_MODEL"
			else if errMsg contains "lms' CLI not found" then
				set errorSummary to "LM Studio CLI not installed"
			else if errMsg contains "Model setup failed" then
				set errorSummary to "Failed to load LM Studio model"
			else if length of errMsg > 100 then
				set errorSummary to (text 1 thru 100 of errMsg) & "..."
			end if
			display notification errorSummary with title "Google Alert Intelligence" subtitle "Setup Required"
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
