import traceback

try:
	from main import main

	main()
except Exception as e:
	traceback.print_exc()
	input("\n\n\nPress Enter to exit... Make sure to take a screenshot and copy all the text above.")
