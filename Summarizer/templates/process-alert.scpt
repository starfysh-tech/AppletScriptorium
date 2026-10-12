using terms from application "Mail"
	on perform mail action with messages theMessages for rule theRule
		-- Log execution for debugging
		set logFile to "{{REPO_PATH}}/runs/mail-rule-execution.log"
		my log_line("Mail rule triggered", logFile)

		set repoPath to "{{REPO_PATH}}"
		set digestRecipient to "{{EMAIL}}"
		-- Python path configured during setup (selected by user based on available installations)
		set pythonPath to "{{PYTHON_PATH}}"

		-- Mail can hand one rule several matching messages at once
		repeat with triggerMessage in theMessages
			my process_message(triggerMessage, repoPath, digestRecipient, pythonPath, logFile)
		end repeat
	end perform mail action with messages
end using terms from

on process_message(triggerMessage, repoPath, digestRecipient, pythonPath, logFile)
	using terms from application "Mail"
		-- The message id keeps two alerts that arrive in the same second apart
		set timestamp to do shell script "date +%Y%m%d-%H%M%S"
		set outputDir to repoPath & "/runs/alert-" & timestamp & "-" & (id of triggerMessage)

		try
			do shell script "mkdir -p " & quoted form of outputDir
			set msgSubject to subject of triggerMessage
			my log_line("Subject: " & msgSubject & " | From: " & (sender of triggerMessage), logFile)
			if msgSubject does not contain "Google Alert" then
				my log_line("WARNING: Non-Google Alert email captured! Subject: " & msgSubject, logFile)
			end if
			my write_text_to_file(source of triggerMessage, outputDir & "/alert.eml")
		on error errMsg
			display notification "Failed to save alert: " & errMsg with title "Google Alert Intelligence"
			return
		end try

		try
			set pythonCmd to "cd " & quoted form of repoPath & " && PYTHONPATH=" & quoted form of repoPath & " " & quoted form of pythonPath & " -m Summarizer.cli run --output-dir " & quoted form of outputDir & " --email-digest " & quoted form of digestRecipient & " --smtp-send 2>&1"
			do shell script pythonCmd
			display notification "Google Alert digest sent to " & digestRecipient with title "Google Alert Intelligence" sound name "Glass"
		on error errMsg
			set errorSummary to errMsg
			if errMsg contains "not found - check .env" then
				set errorSummary to "LM Studio model not found - check .env LMSTUDIO_PREFERRED_MODELS"
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

		-- A failed alert stays unread so it is easy to find and rerun
		set read status of triggerMessage to true
	end using terms from
end process_message

on log_line(message, logFile)
	set timestamp to do shell script "date '+%Y-%m-%d %H:%M:%S'"
	do shell script "echo " & quoted form of (timestamp & " - " & message) & " >> " & quoted form of logFile
end log_line

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
