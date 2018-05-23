import os,sys,shutil,io
import subprocess
import hashlib,tarfile
from subprocess import Popen, PIPE
def mkdir(path,logger=''):
	path=path.strip()
	path=path.rstrip("\\")
	isExists=os.path.exists(path)
	# get result
	if not isExists:
		os.makedirs(path)
		logger.info('mkdir success %s',path)
		return True
	else:
		logger.error('mkdir failed %s,path already exist',path)
		return False
def run_shell(cmd,logger=''):
	logger.info("begin to run cmd:%s", str(cmd))
	rc = 1
	stdout = stderr = ""
	try:
		p = Popen(cmd, shell = True, stdout = PIPE, stderr = PIPE)
		stdout, stderr = p.communicate()
		rc = p.returncode
		if(rc == 0):
			logger.info("run cmd %s success, rc:%s, stdout:%s, stderr:%s",str(cmd),rc,stdout,stderr)
			return  rc, stdout, stderr
		else:
			logger.error("run cmd %s faild, rc:%s, stdout:%s, stderr:%s",str(cmd),rc,stdout,stderr)
			return 	rc, stdout, stderr
	except Exception, msg:
		logger.error("run cmd faild, rc:%s, stdout:%s, stderr:%s", rc, stdout, stderr)
		return rc, "", ""
def hdfs_file_copy(hdfs_file, local_file, force = False, hadoop_bin = "/usr/bin/hadoop",logger=''):
	logger.info("copy hdfs_file:%s to local:%s.", hdfs_file, local_file)
	cmd = "%s fs -get %s %s" % (hadoop_bin, hdfs_file, local_file)
	rc = 1
	if force:  
		cmd = cmd + " -f"
	rc, stdout, stderr = run_shell(cmd,logger)
	return rc
def rsync_file(remote_path,local_path,logger=''):
	cmd = "rsync -av %s %s/" % (remote_path,local_path)
	rc, stdout, stderr = run_shell(cmd,logger)
	return rc == 0
#delete all file in path,not include path itself
def del_file(path,logger=''):
	for i in os.listdir(path):
	#get abs path of file
		path_file = os.path.join(path,i)  
		if os.path.isfile(path_file):
			os.remove(path_file)
		else:
			del_file(path_file)
			os.rmdir(path_file)

#delete all file in path,including path itself
def del_dir(path,logger=''):
	for i in os.listdir(path):
	#get abs path of file
		path_file = os.path.join(path,i)  
		if os.path.isfile(path_file):
			os.remove(path_file)
		else:
			del_file(path_file)
			os.rmdir(path_file)
	os.rmdir(path)  
def copy_file(src_file,dst_file,logger=''):
	if not os.path.isfile(src_file):
		logger.error("%s not exist!",src_file)
		return False
	else:
		fpath,fname=os.path.split(dst_file)    #split file and path
		if not os.path.exists(fpath):
			os.makedirs(fpath)                #create file path
        shutil.copyfile(src_file,dst_file)      #copy file
	return True
#full text replace within  a file 
def copy_dir(src_dir,dst_dir,logger=''):
	if not os.path.exists(src_dir):
		err_msg='copy_dir :%s no exsist' ('src_dir')
		logger.error(err_msg)
		return False,err_msg
	if  os.path.exists(dst_dir):
		del_dir(dst_dir,logger)
	shutil.copytree(src_dir,dst_dir)
	return True,''
def text_replace(file_path,src_content,dst_content,logger=''):
	if not os.path.isfile(file_path):
		logger.error("%s not exist!",file_path)
		return False
	#read file in memory
	with io.open(file_path,"r",encoding='utf-8') as f:
		lines = f.readlines()
	f.close()
	#open file in write mode
	with io.open(file_path,"w",encoding='utf-8') as f_w:
    		for line in lines:
			if src_content in line:
         		#replcae
				line = line.replace(src_content,dst_content)
        		f_w.write(line)
	f_w.close
	return True
def gen_file_md5(file_path,file_name,version,logger=''):
	md5=get_file_md5(file_name)
	outfile_name=os.path.join(file_path,version+'.md5')
	outfile = open(outfile_name,'w')
	outfile.write(md5)
	outfile.close()
	return md5
def get_file_md5(file_name):
	md5file=open(file_name,'rb')
	md5=hashlib.md5(md5file.read()).hexdigest()
	md5file.close()
	return md5
def tar(source_dir,logger=''):
	tarname=source_dir + ".tar.gz"
	tar = tarfile.open(tarname,"w:gz")
	for root,dir,files in os.walk(source_dir):
		root_ = os.path.relpath(root,start=source_dir) 
		for file in files:
			pathfile = os.path.join(root, file)
			tar.add(pathfile,arcname=os.path.join(root_,file))
	tar.close() 
	return tarname
def un_tar(file_name):
	fpath,fname=os.path.split(file_name)
	tar = tarfile.open(file_name)
	names = tar.getnames()
	for name in names:
		tar.extract(name,fpath)
	tar.close()

