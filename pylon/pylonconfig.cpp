#include <sys/types.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <getopt.h>

#include <iostream>
#include <string>

#include <pylon/PylonIncludes.h>
#include <pylon/gige/BaslerGigEInstantCamera.h>

typedef Pylon::CBaslerGigEInstantCamera Camera_t;
using namespace Basler_GigECameraParams;

using namespace Pylon;

// The name of the pylon feature stream file.
const char Filename[] = "NodeMap.pfs";

std::string folder_2_save_pylon_stream_file = ".";
float frame_rate = 1;
int AOI_width = 2048;
int AOI_height = 2048;
int AOI_x_offset = 0;
int AOI_y_offset = 0;

void parse_arguments (int argc, char *argv[]);
int64_t Adjust (int64_t val, int64_t minimum, int64_t maximum, int64_t inc);
bool check_output_folder (char *path);
std::string pylon_stream_file_path (const std::string &folder);

int main(int argc, char* argv[])
{
	parse_arguments (argc, argv);
	std::string filename = pylon_stream_file_path (folder_2_save_pylon_stream_file);
	Pylon::PylonAutoInitTerm autoInitTerm;
	try {
		// Only look for cameras supported by Camera_t.
		CDeviceInfo info;
		info.SetDeviceClass (Camera_t::DeviceClass ());

		// Create an instant camera object with the first found camera device matching the specified device class.
		Camera_t camera( CTlFactory::GetInstance().CreateFirstDevice( info));

		std::cout << "Using device " << camera.GetDeviceInfo ().GetModelName () << std::endl;
		camera.Open();
		camera.ExposureTimeRaw = Adjust (35000, camera.ExposureTimeRaw.GetMin (), camera.ExposureTimeRaw.GetMax (), camera.ExposureTimeRaw.GetInc ());
		//camera.BalanceWhiteAuto = BalanceWhiteAuto_Off;
		camera.AcquisitionFrameRateAbs = frame_rate;
		camera.Width = AOI_width;
		camera.Height = AOI_height;
		camera.OffsetX = AOI_x_offset;
		camera.OffsetY = AOI_y_offset;
		// Enable time stamp chunks.
		camera.ChunkSelector.SetValue (ChunkSelector_Timestamp);
		camera.ChunkEnable.SetValue (true);
		std::cout << "Saving camera's node map to file..." << std::endl;
		// Save the content of the camera's node map into the file.
		CFeaturePersistence::Save (filename.c_str (), &camera.GetNodeMap() );
		// Close the camera.
		camera.Close ();
	}
	catch (const GenericException & e) {
		std::cerr << "An exception occured. Reason: " << e.GetDescription () << std::endl;
	}
	return 0;
}


// Adjust value so it complies with range and increment passed.
//
// The parameter's minimum and maximum are always considered as valid values.
// If the increment is larger than one, the returned value will be: min + (n * inc).
// If the value doesn't meet these criteria, it will be rounded down so that it does.
int64_t Adjust (int64_t val, int64_t minimum, int64_t maximum, int64_t inc)
{
	// Check the input parameters.
	if (inc <= 0) {
		throw LOGICAL_ERROR_EXCEPTION ("Unexpected increment %d", inc);
	}
	if (minimum > maximum) {
		throw LOGICAL_ERROR_EXCEPTION ("minimum bigger than maximum.");
	}
	if (val < minimum) {
		return minimum;
	}
	if (val > maximum) {
		return maximum;
	}
	// Check the increment.
	if (inc == 1) {
		// Special case: all values are valid.
		return val;
	}
	else {
		// The value must be min + (n * inc).
		// Due to the integer division, the value will be rounded down.
		return minimum + ( ((val - minimum) / inc) * inc );
	}
}

bool check_output_folder (char *path)
{
	struct stat m;
	int res = stat (path, &m);
	return res == 0 && (m.st_mode & S_IFMT) == S_IFDIR;
}

std::string pylon_stream_file_path (const std::string &folder)
{
	time_t t;
	struct tm tm;
	time (&t);
	gmtime_r (&t, &tm);
	std::string result;
	result += folder;
	result += "/pylon-cfg_";
	char timestamp [30];
	sprintf (timestamp, "%04d-%02d-%02d+%02d:%02d:%02d",
	  tm.tm_year + 1900,
	  tm.tm_mon + 1,
	  tm.tm_mday,
	  tm.tm_hour,
	  tm.tm_min,
	  tm.tm_sec);
	result += timestamp;
	result += ".pfs";
	return result;
}

void parse_arguments (int argc, char *argv[])
{
	static struct option long_options[] = {
		{
			.name = "frame-rate",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'f'
		},
		{
			.name = "output-folder",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'o'
		},
		{
			.name = "width",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'w'
		},
		{
			.name = "height",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'h'
		},
		{
			.name = "x-offset",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'x'
		},
		{
			.name = "y-offset",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'y'
		},
		{0, 0, 0, 0}

	};
	while (1) {
		int option_index;
		int c = getopt_long (argc, argv, "f:o:w:h:", long_options, &option_index);
		switch (c) {
		case 'f':
			if (sscanf (optarg, "%f", &frame_rate) != 1) {
				std::cerr << "Option " << optarg << " is not a floating point number!\n";
				exit (EXIT_FAILURE);
			}
			break;
		case 'o':
			if (!check_output_folder (optarg)) {
				std::cerr << "Folder " << optarg << " does not exist!\n";
				exit (EXIT_FAILURE);
			}
			folder_2_save_pylon_stream_file = optarg;
			break;
		case 'w':
			if (sscanf (optarg, "%d", &AOI_width) != 1) {
				std::cerr << "AOI width option " << optarg << " is not an integer number!\n";
				exit (EXIT_FAILURE);
			}
			break;
		case 'h':
			if (sscanf (optarg, "%d", &AOI_height) != 1) {
				std::cerr << "AOI height option " << optarg << " is not an integer number!\n";
				exit (EXIT_FAILURE);
			}
			break;
		case 'x':
			if (sscanf (optarg, "%d", &AOI_x_offset) != 1) {
				std::cerr << "AOI x offset option " << optarg << " is not an integer number!\n";
				exit (EXIT_FAILURE);
			}
			break;
		case 'y':
			if (sscanf (optarg, "%d", &AOI_y_offset) != 1) {
				std::cerr << "AOI y offset option " << optarg << " is not an integer number!\n";
				exit (EXIT_FAILURE);
			}
			break;
		case -1:
			return ;
		}
	}
}

