
import os
import re
import logging

logger = logging.getLogger(__name__)

class NewFileReader:

    FRONT_FILE_LOC  = "/data/external/frontfile"
    BACK_FILE_LOC   = "/data/external/backfile"
    NEW_FILES_LOC   = FRONT_FILE_LOC + "/{0}/{1}/{2:02d}"
    YEAR_FILES_LOC  = BACK_FILE_LOC + "/{0}"
    NEW_FILES_NAME  = "newfiles.txt"

    SUFFIX_CHEM    = ".chemicals.tsv.gz"
    SUFFIX_BIBLIO  = ".biblio.json.gz"

    SUPP_CHEM_REGEX = r"_supp[0-9]+.chemicals.tsv.gz"
    FILE_PATH_REGEX = r"(.*/)([^/]+$)"

    def __init__(self, ftp):
        '''
        Initializes the NewFileReader
        :param ftp: Instance of ftplib.FTP, already initialized and ready for server interaction.
        '''

        self.ftp = ftp
        self.supp_regex = re.compile(self.SUPP_CHEM_REGEX)


    def new_files(self, from_date):
        '''
        Reads the list of new files from the FTP server, for the given date.
        :param from_date: The date to query
        :return: List of file path strings, retrieved from the list of new files. File path strings
        will be absolute paths on the FTP server.
        '''

        logger.info( "Identifying new files for {}".format(from_date) )

        # TODO assert date object?
        new_files_loc = self.NEW_FILES_LOC.format(
            from_date.year,
            from_date.month,
            from_date.day)

        # TODO gracefully handle missing directory
        self.ftp.cwd( new_files_loc )

        data = []
        def handle_binary(more_data):
            data.append(more_data)

        # TODO gracefully handle missing file
        self.ftp.retrbinary("RETR " + self.NEW_FILES_NAME, handle_binary)

        content = "".join(data)
        rel_file_list = content.split('\n')
        abs_file_list = map( lambda f: "{0}/{1}".format(self.FRONT_FILE_LOC, f), rel_file_list)

        logger.info( "Discovered {} new files".format(len(abs_file_list)) )

        return abs_file_list

    def year_files(self, date_obj):

        year = date_obj.year
        logger.info( "Identifying files for year {}".format(year) )

        year_path = self.YEAR_FILES_LOC.format(year)

        self.ftp.cwd( year_path )
        ftp_file_list = self.ftp.nlst()
        abs_file_list = map( lambda f: "{0}/{1}".format(year_path, f), ftp_file_list)

        logger.info( "Discovered {} files".format(len(abs_file_list)) )

        return abs_file_list

    def select_downloads(self, file_list):

        logger.info( "Selecting files to download" )

        bibl_files = set()
        chem_files = set()

        for file in file_list:
            if file.endswith(self.SUFFIX_BIBLIO):
                bibl_files.add(file)
            elif file.endswith(self.SUFFIX_CHEM):
                chem_files.add(file)

        supp_chems = filter( lambda f: self.supp_regex.search(f), file_list )

        for sc in supp_chems:
            bibl_files.add( self.supp_regex.sub(self.SUFFIX_BIBLIO, sc) )

        download_list = sorted(bibl_files) + sorted(chem_files)

        logger.info( "Selected {} files for download".format( len(download_list) ) )

        return download_list


    def read_files(self,file_list,target_dir):
        '''
        Download the given files from the FTP server, into the given target folder.
        :param file_list: List of file paths, relative to the FTP server
        :param target_dir: Local file path to store the downloads in; will be created if non-existent
        '''
        # TODO add python docs throughout

        logger.info( "Creating target directory for download: [{}]".format(target_dir) )
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, mode=0755)

        for file_path in file_list:

            matched = re.match(self.FILE_PATH_REGEX, file_path)
            path = matched.group(1)
            file = matched.group(2)

            fhandle = open("{0}/{1}".format(target_dir,file), 'wb')

            logger.info("Changing to remote directory [{}]".format(path))
            logger.info("Downloading [{}]".format(file))

            self.ftp.cwd( path )
            self.ftp.retrbinary("RETR " + file, fhandle.write)
            # TODO resilient download / error checking / retry

            fhandle.close()


