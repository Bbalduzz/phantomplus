import sys
def progress_bar(total, progress, textname):
	barLength, status = 20, ""
	progress = float(progress) / float(total)
	if progress >= 1.:
		progress, status = 1, "\r\n"
	block = int(round(barLength * progress))
	text = "\r[+] Merging: {} [{}] {:.0f}% {}".format(
		textname, "#" * block + "-" * (barLength - block), round(progress * 100, 0),
		status)
	sys.stdout.write(text)
	sys.stdout.flush()