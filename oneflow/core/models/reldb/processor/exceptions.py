# -*- coding: utf-8 -*-
u"""
Copyright 2015 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/
"""


class ProcessorException(Exception):

    """ Raised in the processor when a problem is encountered. """

    pass


class StopProcessingException(ProcessorException):

    """ Raised when the current processor asks to stop the chain. """

    pass


class InstanceNotAcceptedException(ProcessorException):

    """ Raised when an instance was not accepted during processing.

    Used in the processor chain, which avoid running accepts()
    then process(): it runs process() directly, which runs accepts()
    implicitely. process() will raise this exception if accepts()
    doesn't return True.

    This exception should not be raised in accepts() code, it's for
    this particular internal use only.
    """

    pass


class ProcessorSecurityException(ProcessorException):

    """ Raised when some code shows a security risk. """

    pass
