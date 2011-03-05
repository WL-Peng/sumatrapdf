"""
Updates the dependency lists in makefile.msvc for all object files produced
from sources in baseutils and src, so that changing a header file always leads
to the recompilation of all the files depending on this header.
"""

import os, re, fnmatch
from util import verify_started_in_right_directory

def pjoin(*args):
	return os.path.join(*args).replace("/", "\\")

DIRS = ["baseutils", "src", pjoin("src", "installer"), pjoin("src", "ifilter"), pjoin("src", "browserplugin")]
INCLUDE_DIRS = DIRS + [pjoin("mupdf", "mupdf"), pjoin("mupdf", "fitz")]
MAKEFILE = "makefile.msvc"
DEPENDENCIES_PER_LINE = 3

def memoize(func):
	memory = {}
	def __decorated(*args):
		if args not in memory:
			memory[args] = func(*args)
		return memory[args]
	return __decorated

def group(list, size):
	i = 0
	while list[i:]:
		yield list[i:i + size]
		i += size

def uniquify(array):
	return list(set(array))

def prependPath(files, basefile=None):
	result = []
	include_dirs = INCLUDE_DIRS
	if basefile:
		include_dirs = [os.path.split(basefile)[0]] + include_dirs
	
	for file in files:
		for dir in include_dirs:
			path = pjoin(dir, file)
			if os.path.exists(path):
				result.append(path)
				break
	return result

@memoize
def extractIncludes(file):
	content = open(file, "r").read()
	includes = re.findall(r'(?m)^#include ["<]([^">]+)[">]', content)
	includes = [path.replace("/", os.path.sep) for path in includes]
	includes = prependPath(includes, file)
	
	for inc in includes:
		includes += extractIncludes(inc)
	return uniquify(includes)

def createDependencyList():
	dependencies = {}
	for dir in DIRS:
		all_c_files = fnmatch.filter(os.listdir(dir), "*.c*")
		for file in all_c_files:
			file = pjoin(dir, file)
			dependencies[file] = extractIncludes(file)
	return dependencies

def flattenDependencyList(dependencies):
	flatlist = []
	for file in dependencies.keys():
		if dependencies[file]:
			filename = os.path.splitext(os.path.split(file)[1])[0]
			deplist = sorted(dependencies[file], key=str.lower)
			for depgroup in group(deplist, DEPENDENCIES_PER_LINE):
				flatlist.append("$(O)\\%s.obj: %s" % (filename, " ".join(depgroup)))
	return flatlist

def injectDependencyList(flatlist):
	content = open(MAKEFILE, "rb").read().replace("\r\n", "\n")
	content = re.sub(r"(?ms)^### the list [^\n]+ update_dependencies\.py.*|\Z", "", content)
	
	flatlist = "\n".join(sorted(flatlist, key=str.lower))
	content += "### the list below is auto-generated by update_dependencies.py\n" + flatlist + "\n"
	
	open(MAKEFILE, "wb").write(content.replace("\n", "\r\n"))

def main():
	if os.path.exists("update_dependencies.py"):
		os.chdir("..")
	verify_started_in_right_directory()
	
	injectDependencyList(flattenDependencyList(createDependencyList()))

if __name__ == "__main__":
	main()
