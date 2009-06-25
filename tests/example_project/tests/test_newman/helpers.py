from datetime import datetime, timedelta
from time import sleep

from djangosanetesting import SeleniumTestCase

__all__ = ("NewmanTestCase", "DateTimeAssert")

class FormAssertSpec(object):
    """
    Interface for form assertion specification.
    Overwrite is_equal for more sophisticated methods in assert_form
    """
    def __init__(self, expected_value, value_function_name="get_value"):
        super(FormAssertSpec, self).__init__()
        self.expected_value = expected_value
        self.value_function_name = value_function_name

    def is_equal(self, retrieved_value):
        return retrieved_value == self.expected_value

#class RegexpAssert(FormAssertSpec):
#    def is_equal(self, retrieved_value):
#        return re.match(self.expected_value, retrieved_value)

class DateTimeAssert(FormAssertSpec):
    """
    When datetime is autogenerated on client, submitted and asserted, we're in
    unfortunate situation when we have not-synced time.
    So we'll do fuzzy matching: dates are equal, if difference between them is
    less then allowed_delta (default to half minute).
    """
    def __init__(self, expected_value, value_function_name="get_value",
            date_format="%Y-%m-%d %H:%M", allowed_delta=None):
        super(DateTimeAssert, self).__init__(expected_value, value_function_name)

        self.date_format = date_format
        self.allowed_delta = allowed_delta or timedelta(minutes=1)

    def is_equal(self, retrieved_value):
        retrieved_time = datetime.strptime(retrieved_value, self.date_format)

        if retrieved_time > self.expected_value:
            return (retrieved_time - self.expected_value) <= self.allowed_delta

        else:
            return (self.expected_value - retrieved_time) <= self.allowed_delta


class NewmanTestCase(SeleniumTestCase):
    fixtures = ['newman_admin_user', 'example_data']

    USER_USERNAME = u"superman"
    USER_PASSWORD = u"xxx"

    NEWMAN_URI = "/newman/"

    def __init__(self):
        super(NewmanTestCase, self).__init__()
        self.elements = {
            'navigation' : {
                'logout' : "//a[@class='icn logout']",
                'categories' : "//a[@class='app category']",
                'categories_add' : "//a[@class='app category']/../a[position()=2]",
                'articles' : "//a[@class='app article']",
                'article_add' : "//a[@class='app article']/../a[position()=2]",
                'galleries' : "//a[@class='app gallery']",
            },
            'controls' : {
                'suggester' : "//div[@class='suggest-bubble']",
                'suggester_visible' : "//span[@class='hilite']",
                'suggester_selected' : "//input[@id='id_%(field)s']/../ul/li[@class='suggest-selected-item']",
                'message' : {
                    'ok': "//div[@id='opmsg']/span[@class='okmsg']",
                },
                'add' : "//a[@class='js-hashadr icn btn add']",
                'save' : "//a[@class='js-submit icn btn save def']",
                'show_filters' : "//div[@id='filters-handler']/a[position()=1]",
                'lookup_content' : "//div[@id='changelist']/form/table/tbody/tr/th/a[text()='%(text)s']",
                'search_button' : "//a[@class='btn icn search def']",
            },
            'pages' : {
                'login' : {
                    'submit' : "//input[@type='submit']"
                },
                'listing' : {
                    'first_object' : "//div[@id='changelist']/form/table/tbody/tr[position()='1']",
                    'object' : "//div[@id='changelist']/form/table/tbody/tr[position()='%(position)s']",
                    'object_href' : "//div[@id='changelist']/form/table/tbody/tr[position()='%(position)s']/th/a[position()=2]",
                    'datepicker' : "//td[@class='%(field)s']/span[@class='dtpicker-trigger']",
                    'calendar_day' : "//table[@class='ui-datepicker-calendar']/tbody/tr/td/a[text()='%(day)s']",
                }
            }
        }

    def setUp(self):
        super(NewmanTestCase, self).setUp()
        self.login()

    def login(self):
        self.selenium.open(self.NEWMAN_URI)
        self.selenium.type("id_username", self.USER_USERNAME)
        self.selenium.type("id_password", self.USER_PASSWORD)
        self.selenium.click(self.elements['pages']['login']['submit'])
        self.selenium.wait_for_page_to_load(30000)
        # give javascript time to settle
        sleep(0.2)

    def logout(self):
        self.selenium.click(self.elements['navigation']['logout'])
        # we should be on login page
        self.selenium.wait_for_element_present('id_username')

    def tearDown(self):
        self.logout()
        super(NewmanTestCase, self).tearDown()


    def get_listing_object(self, position=1):
        return self.elements['pages']['listing']['object'] % {
            'position' : position
        }

    def get_listing_object_href(self, position=1):
        return self.elements['pages']['listing']['object_href'] % {
            'position' : position
        }

    def fill_fields(self, data):
        s = self.selenium
        for key, value in data.items():
            s.type('id_%s' % key, value)

    def fill_suggest_fields(self, suggest_data):
        s = self.selenium
        for key, values in suggest_data.items():
            for value in values:
                id = 'id_%s_suggest' % key
                s.click(id)
                s.type(id, value)
                s.click(id)
                s.wait_for_element_present(self.elements['controls']['suggester_visible'])
                s.click(self.elements['controls']['suggester_visible'])

    def fill_calendar_fields(self, calendar_data):
        """
        Select date from calendars. Calendar_data is dict in form of {
            "field" : {
                "day" : int,
            }
        }, where day of the current month is selected.
        (support for other fields is TODO)
        """
        s = self.selenium
        for field in calendar_data:
            # click on calendar button
            xpath = self.elements['pages']['listing']['datepicker'] % {
                "field" : field
            }
            s.click(xpath)

            # chose the current date
            xpath = self.elements['pages']['listing']['calendar_day'] % {
                "day" : calendar_data[field]['day']
            }
            s.click(xpath)


    def fill_using_lookup(self, data):
        """
        Fill data using "magnifier".
        @param data is dictionary of fields and values, in form:
        {
            "field" : "value",
        }
        where field is name of field magnifier is bound to and value is a content of the element from the list
        """
        s = self.selenium
        for field in data:
            xpath = "lookup_id_%s" % field
            s.click(xpath)
            s.click(self.elements['controls']['lookup_content'] % {'text' : data[field]})

    def save_form(self):
        s = self.selenium
        s.click(self.elements['controls']['save'])
        s.wait_for_element_present(self.elements['controls']['message']['ok'])

    def get_formatted_form_errors(self, errors):
        messages = []
        for field in errors:
            expected = errors[field]['expected']
            retrieved = errors[field]['retrieved']

            if isinstance(expected, list):
                expected = u"".join(expected)

            if isinstance(retrieved, list):
                retrieved = u"".join(retrieved)

            messages.append("Form validation for field %(field)s was expecting %(expected)s, but got %(retrieved)s" % {
                'field' : field,
                'expected' : expected,
                'retrieved' : retrieved,
            })

        return u'\n'.join(messages).encode('utf-8')

    def add_error(self, errors, field, expected, retrieved):
        errors[field] = {
            'expected' : expected,
            'retrieved' : retrieved,
        }
        return errors


    def verify_form(self, data):
        errors = {}
        for field in data:
            spec = data[field]
            if isinstance(spec, FormAssertSpec):
                text = getattr(self.selenium, spec.value_function_name)('id_%s' % field)
                if not spec.is_equal(text):
                    self.add_error(errors, field, spec.expected_value, text)

            elif isinstance(spec, list):
                for i in xrange(0, len(spec)):
                    xpath = (self.elements['controls']['suggester_selected']+"[%(number)s]") % {
                        'field' : field,
                        'number' : i+1, # xpath indexes from 1 :]
                    }
                    text = self.selenium.get_text(xpath)
                    if text != spec[i]:
                        self.add_error(errors, field, spec, text)

            else:
                text = self.selenium.get_value('id_%s' % field)
                if text != spec:
                    self.add_error(errors, field, spec, text)

        if len(errors) > 0:
            raise AssertionError(self.get_formatted_form_errors(errors))

