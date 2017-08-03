#include <sys/types.h>
#include <sys/stat.h>
#include <time.h>
#include <math.h>
#include <unistd.h>
#include <getopt.h>

// Include files to use the PYLON API
#include <pylon/PylonIncludes.h>
#ifdef PYLON_WIN_BUILD
#    include <pylon/PylonGUI.h>
#endif
// Namespace for using pylon objects.
using namespace Pylon;
#if defined( USE_1394 )
// Settings for using Basler IEEE 1394 cameras.
#include <pylon/1394/Basler1394InstantCamera.h>
typedef Pylon::CBasler1394InstantCamera Camera_t;
typedef Pylon::CBasler1394ImageEventHandler ImageEventHandler_t; // Or use Camera_t::ImageEventHandler_t
typedef Pylon::CBasler1394GrabResultPtr GrabResultPtr_t; // Or use Camera_t::GrabResultPtr_t
using namespace Basler_IIDC1394CameraParams;
#elif defined ( USE_GIGE )
// Settings for using Basler GigE cameras.
#include <pylon/gige/BaslerGigEInstantCamera.h>
typedef Pylon::CBaslerGigEInstantCamera Camera_t;
typedef Pylon::CBaslerGigEImageEventHandler ImageEventHandler_t; // Or use Camera_t::ImageEventHandler_t
typedef Pylon::CBaslerGigEGrabResultPtr GrabResultPtr_t; // Or use Camera_t::GrabResultPtr_t
using namespace Basler_GigECameraParams;
#elif defined( USE_USB )
// Settings for using Basler USB cameras.
#include <pylon/usb/BaslerUsbInstantCamera.h>
typedef Pylon::CBaslerUsbInstantCamera Camera_t;
typedef Pylon::CBaslerUsbImageEventHandler ImageEventHandler_t; // Or use Camera_t::ImageEventHandler_t
typedef Pylon::CBaslerUsbGrabResultPtr GrabResultPtr_t; // Or use Camera_t::GrabResultPtr_t
using namespace Basler_UsbCameraParams;
#else
#error Camera type is not specified. For example, define USE_GIGE for using GigE cameras.
#endif
// Namespace for using cout.
using namespace std;

Camera_t *camera;
int number_frames;
string frames_folder;
string timestamp_folder;

void parse_arguments (int argc, char *argv[]);
void op_record (int number_frames, string image_folder, string timestamp_folder);

int main(int argc, char* argv[])
{
	// The exit code of the sample application.
	int exitCode = 0;
	// Before using any pylon methods, the pylon runtime must be initialized. 
	PylonInitialize ();
	try {
		// Only look for cameras supported by Camera_t
		CDeviceInfo info;
		info.SetDeviceClass (Camera_t::DeviceClass ());
		// Create an instant camera object with the first found camera device that matches the specified device class.
		camera = new Camera_t (CTlFactory::GetInstance ().CreateFirstDevice (info));
		// Print the model name of the camera.
		cout << "Using device " << camera->GetDeviceInfo ().GetModelName () << endl;
		// Open the camera.
		camera->Open ();
		// A GenICam node map is required for accessing chunk data. That's why a small node map is required for each grab result.
		// Creating a lot of node maps can be time consuming.
		// The node maps are usually created dynamically when StartGrabbing() is called.
		// To avoid a delay caused by node map creation in StartGrabbing() you have the option to create
		// a static pool of node maps once before grabbing.
		//camera->StaticChunkNodeMapPoolSize = camera->MaxNumBuffer.GetValue();
		// Enable chunks in general.
		if (GenApi::IsWritable (camera->ChunkModeActive)) {
			camera->ChunkModeActive.SetValue (true);
		}
		else {
			throw RUNTIME_EXCEPTION( "The camera doesn't support chunk features");
		}
		// Enable time stamp chunks.
		camera->ChunkSelector.SetValue (ChunkSelector_Timestamp);
		camera->ChunkEnable.SetValue (true);
		// test the operation record
		op_record (600, ".", ".");
		// Disable chunk mode.
		camera->ChunkModeActive.SetValue(false);

		delete camera;
	}
	catch (const GenericException &e) {
		// Error handling.
		cerr << "An exception occurred." << endl
			  << e.GetDescription () << endl;
		exitCode = 1;
	}
	// Releases all pylon resources. 
	PylonTerminate (); 
	return exitCode;
}


void op_record (int number_images, string image_folder, string timestamp_folder)
{
	string timestamp_path = timestamp_folder + "/timestamp.csv";
	FILE *timestamp_file = fopen (timestamp_path.c_str (), "w");
	const char prefix[] = "/image-";
	const char suffix[] = ".png";
	char *image_filename = new char (strlen (prefix) + strlen (suffix) + ceil (log10 (number_images)) + 1);
	string image_path;
	int image_counter = 1;
	// The camera device is parameterized with a default configuration which
	// sets up free-running continuous acquisition.
	camera->StartGrabbing (number_images);
	// This smart pointer will receive the grab result data.
	GrabResultPtr_t ptrGrabResult;
	// Camera.StopGrabbing() is called automatically by the RetrieveResult() method
	// when c_countOfImagesToGrab images have been retrieved.
	while (camera->IsGrabbing ()) {
		// Wait for an image and then retrieve it. A timeout of 5000 ms is used.
		camera->RetrieveResult (5000, ptrGrabResult, TimeoutHandling_ThrowException);
		struct timespec res;
		if (clock_gettime (CLOCK_REALTIME, &res) == -1) {
			perror ("getting the clock after obtained an image from the basler camera");
			delete camera;
			PylonTerminate ();
			exit (EXIT_FAILURE);
		}
		cout << "GrabSucceeded: " << ptrGrabResult->GrabSucceeded () << endl;
		if (ptrGrabResult->GrabSucceeded ()) {
			// The result data is automatically filled with received chunk data.
			// (Note:  This is not the case when using the low-level API)
			cout << "SizeX: " << ptrGrabResult->GetWidth () << endl;
			cout << "SizeY: " << ptrGrabResult->GetHeight () << endl;
			const uint8_t *pImageBuffer = (uint8_t *) ptrGrabResult->GetBuffer();
			// Check to see if a buffer containing chunk data has been received.
			if (PayloadType_ChunkData != ptrGrabResult->GetPayloadType ()) {
				throw RUNTIME_EXCEPTION ("Unexpected payload type received.");
			}
			// Access the chunk data attached to the result.
			// Before accessing the chunk data, you should check to see
			// if the chunk is readable. When it is readable, the buffer
			// contains the requested chunk data.
			if (IsReadable (ptrGrabResult->ChunkTimestamp))
				cout << "TimeStamp (Result): " << ptrGrabResult->ChunkTimestamp.GetValue () << endl;
			fprintf (timestamp_file, "%ld,%ld,%ld\n", ptrGrabResult->ChunkTimestamp.GetValue (), res.tv_sec, res.tv_nsec);
			sprintf (image_filename, "%s%04d%s", prefix, image_counter, suffix);
			image_path = image_folder + image_filename;
			CImagePersistence::Save (ImageFileFormat_Png, image_path.c_str (), ptrGrabResult);
			cout << endl;
			image_counter++;
		}
	}
	fclose (timestamp_file);
	delete image_filename;
}

bool check_folder (char *path)
{
	struct stat m;
	int res = stat (path, &m);
	return res == 0 && (m.st_mode & S_IFMT) == S_IFDIR;
}

void parse_arguments (int argc, char *argv[])
{
	static struct option long_options[] = {
		{
			.name = "number-frames",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'n'
		},
		{
			.name = "frames-folder",
			.has_arg = required_argument,
			.flag = 0,
			.val = 'f'
		},
		{
			.name = "timestamp-folder",
			.has_arg = required_argument,
			.flag = 0,
			.val = 't'
		},
		{0, 0, 0, 0}
	};
	while (1) {
		int option_index;
		int c = getopt_long (argc, argv, "n:f:t:h", long_options, &option_index);
		switch (c) {
		case 'n':
			if (sscanf (optarg, "%d", &number_frames) != 1) {
				std::cerr << "Option " << optarg << " is not an integer number!\n";
				exit (EXIT_FAILURE);
			}
			break;
		case 'f':
			if (!check_folder (optarg)) {
				std::cerr << "Folder " << optarg << " does not exist!\n";
				exit (EXIT_FAILURE);
			}
			frames_folder = optarg;
			break;
		case 't':
			if (!check_folder (optarg)) {
				std::cerr << "Folder " << optarg << " does not exist!\n";
				exit (EXIT_FAILURE);
			}
			timestamp_folder = optarg;
			break;
		case 'h':
			printf ("Grabs images from a Basler camera\n");
			printf ("Usage:\n");
			printf ("%s -n N -f PATH -t PATH\n", argv [0]);
			printf ("  -n, --number-frames N        number of images to grab\n");
			printf ("  -f, --frames-folder PATH     path where grabbed images are saved\n");
			printf ("  -t, --timestamp-folder PATH  path were a CSV file with time stamps is saved\n");
			exit (EXIT_SUCCESS);
			break;
		case -1:
			return ;
		default:
			fprintf (stderr, "Unknown option\n");
			exit (EXIT_FAILURE);
			break;
		}
	}
}
