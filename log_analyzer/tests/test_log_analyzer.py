import unittest

from log_analyzer.log_analyzer import get_count_perc, get_med,\
    get_time_avg, get_time_max, get_time_perc, get_time_sum, median


class TestLogAnalyzer(unittest.TestCase):

    test_statistics_data = {'total_events': 28,
                            'urls': {'/test/url': {'count': 14,
                                     'times': [
                                         0.008, 0.905, 0.546, 0.639,
                                         0.607, 0.689, 0.544,
                                         0.912, 1.17, 0.6, 0.635,
                                         0.009, 0.588, 0.817]},
                                     '/test/url2': {'count': 14,
                                                    'times': [
                                                        0.008, 0.905,
                                                        0.546, 0.639,
                                                        0.607, 0.689,
                                                        0.544, 0.912,
                                                        1.17, 0.6,
                                                        0.635, 0.009,
                                                        0.588, 0.817]}
                                     }
                            }

    def test_count_perc(self):
        self.assertEqual(get_count_perc(28,
                                        self.test_statistics_data[
                                            'urls']['/test/url']['count']),
                         50.0)

    def test_median(self):
        self.assertEquals(median([1, 1, 1]), 1)
        self.assertEquals(median([1, 2, 3]), 2)
        self.assertEquals(median([1, 2]), 1.5)
        self.assertEquals(median([1.5, 2.5]), 2.0)
        self.assertEquals(median([1, 2]), 1.5)
        self.assertEquals(median([1.5, 2]), 1.75)
        self.assertEquals(median([]), )
        with self.assertRaises(TypeError):
            median("test_string")
        with self.assertRaises(TypeError):
            median(123)
        with self.assertRaises(TypeError):
            median(['s', '1'])

    def test_time_avg(self):
        self.assertEquals(get_time_avg(self.test_statistics_data[
                                            'urls']['/test/url']['times']),
                          0.6192142857142857)

    def test_time_max(self):
        self.assertEquals(get_time_max(self.test_statistics_data[
                                            'urls']['/test/url']['times']),
                          1.17)

    def test_time_perc(self):
        self.assertEquals(get_time_perc(self.test_statistics_data,
                                        self.test_statistics_data[
                                            'urls']['/test/url']['times']),
                          50.000000000000014)

    def test_time_sum(self):
        self.assertEquals(get_time_sum(self.test_statistics_data[
                                            'urls']['/test/url']['times']),
                          8.669)

    def test_median(self):
        self.assertEquals(get_med(self.test_statistics_data[
                                            'urls']['/test/url']['times']),
                          0.621)


if __name__ == '__main__':
    unittest.main()
