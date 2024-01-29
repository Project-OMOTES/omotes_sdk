#  Copyright (c) 2023. {cookiecutter.cookiecutter.maintainer_name}}
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Main python file for OMOTES SDK Python."""
from datetime import datetime, timedelta

def testable_function(input: datetime):
    """Testable function"""
    return input + + timedelta(hours=1)
    

def start_app(loglevel: str, colors: bool, simulation: str | None) -> None:
    """OMOTES SDK Python application"""
    try:
        setup_logging(LogLevel.parse(loglevel), colors)
        
        # TODO insert your code here

    except Exception as error:
        logger.error(f"Error occured: {error} at: {traceback.format_exc(limit=-1)}")
        logger.debug(traceback.format_exc())

if __name__ == '__main__':
    return_hello_world()
